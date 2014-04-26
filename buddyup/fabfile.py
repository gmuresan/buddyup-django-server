import os
import pdb
import re
import sys
from functools import wraps
from getpass import getpass, getuser
from glob import glob
from contextlib import contextmanager
import getpass as _getpass

from fabric.api import env, cd, prefix, sudo as _sudo, run as _run, hide, task
from fabric.context_managers import warn_only
from fabric.contrib.files import exists, upload_template
from fabric.colors import yellow, green, blue, red

from fabric.operations import local, run


################
# Config setup #
################
from virtualenv import mkdir

conf = {}
if sys.argv[0].split(os.sep)[-1] == "fab":
    # Ensure we import settings from the current dir
    try:
        conf = __import__("settings", globals(), locals(), [], 0).FABRIC
        try:
            conf["HOSTS"][0]
        except (KeyError, ValueError):
            raise ImportError
    except (ImportError, AttributeError):
        print("Aborting, no hosts defined.")
        exit()

env.db_pass = conf.get("DB_PASS", None)
env.admin_pass = conf.get("ADMIN_PASS", None)
env.user = conf.get("SSH_USER", getuser())
env.password = conf.get("SSH_PASS", None)
env.key_filename = conf.get("SSH_KEY_PATH", None)
env.hosts = conf.get("HOSTS", [])

env.proj_name = conf.get("PROJECT_NAME", os.getcwd().split(os.sep)[-1])
env.venv_home = conf.get("VIRTUALENV_HOME", "/home/%s" % env.user)
env.venv_path = "%s/%s" % (env.venv_home, env.proj_name)
env.proj_dirname = "project"
env.proj_path = "%s/%s" % (env.venv_path, env.proj_dirname)
env.manage = "%s/bin/python %s/project/manage.py" % (env.venv_path,
                                                     env.venv_path)
env.live_host = conf.get("LIVE_HOSTNAME", env.hosts[0] if env.hosts else None)
env.repo_url = conf.get("REPO_URL", "")
env.git = env.repo_url.startswith("git") or env.repo_url.endswith(".git")
env.reqs_path = conf.get("REQUIREMENTS_PATH", None)
env.gunicorn_port = conf.get("GUNICORN_PORT", 8000)
env.locale = conf.get("LOCALE", "en_US.UTF-8")
env.python_dir = "/opt/lib/python3.3"

env.num_workers = (os.sysconf("SC_NPROCESSORS_ONLN") * 2) + 1


##################
# Template setup #
##################

# Each template gets uploaded at deploy time, only if their
# contents has changed, in which case, the reload command is
# also run.

templates = {
    "nginx": {
        "local_path": "deploy/nginx.conf",
        "remote_path": "/etc/nginx/sites-enabled/%(proj_name)s.conf",
        "reload_command": "service nginx restart",
    },
    "supervisor": {
        "local_path": "deploy/supervisor.conf",
        "remote_path": "/etc/supervisor/conf.d/%(proj_name)s.conf",
        "reload_command": "supervisorctl reread; supervisorctl reload",
    },
    "cron": {
        "local_path": "deploy/crontab",
        "remote_path": "/etc/cron.d/%(proj_name)s",
        "owner": "root",
        "mode": "600",
    },
    "gunicorn": {
        "local_path": "deploy/gunicorn_start",
        "remote_path": "%(proj_path)s/gunicorn_start",
        "mode": "u+x",
    },
    "settings": {
        "local_path": "deploy/live_settings.py",
        "remote_path": "%(proj_path)s/buddyup/local_settings.py",
    },
}


######################################
# Context for virtualenv and project #
######################################

@task
def localSSH():
    pass
   ### run the following commands ###
    # sudo ssh-add ubuntu (remember the password)
    # sudo visudo (paste the following under user privilege : "ubuntu ALL=(ALL) NOPASSWD: ALL"

    #ssh_file = "~/.ssh/id_dsa_buddyup"
    #local("ssh-keygen -t dsa -P '' -f %s" % ssh_file)
    #local("cat %s.pub >> ~/.ssh/authorized_keys" % ssh_file)
    #env.key_filename = ssh_file
    #env.user = _getpass.getuser()

@task
def localInstall():
    env.host_string = '127.0.0.1'
    env.hosts = ['127.0.0.1']
    install()

@task
def localCreate():
    localSSH()
    env.host_string = '127.0.0.1'
    env.hosts = ['127.0.0.1']

    create()


def wget(path):
    sudo("wget -r -nH --cut-dirs=999 %s" % path)


@contextmanager
def virtualenv():
    """
    Runs commands within the project's virtualenv.
    """
    with cd(env.venv_path):
        with prefix("source %s/bin/activate" % env.venv_path):
            yield


@contextmanager
def project():
    """
    Runs commands within the project's directory.
    """
    with virtualenv():
        with cd(env.proj_dirname):
            yield


@contextmanager
def update_changed_requirements():
    """
    Checks for changes in the requirements file across an update,
    and gets new requirements if changes have occurred.
    """
    reqs_path = os.path.join(env.proj_path, env.reqs_path)
    get_reqs = lambda: run("cat %s" % reqs_path, show=False)
    old_reqs = get_reqs() if env.reqs_path else ""
    yield
    if old_reqs:
        new_reqs = get_reqs()
        if old_reqs == new_reqs:
            # Unpinned requirements should always be checked.
            for req in new_reqs.split("\n"):
                if req.startswith("-e"):
                    if "@" not in req:
                        # Editable requirement without pinned commit.
                        break
                elif req.strip() and not req.startswith("#"):
                    if not set(">=<") & set(req):
                        # PyPI requirement without version.
                        break
            else:
                # All requirements are pinned.
                return
        pip("-r %s/%s" % (env.proj_path, env.reqs_path))


###########################################
# Utils and wrappers for various commands #
###########################################

def _print(output):
    print()
    print(output)
    print()


def print_command(command):
    _print(blue("$ ", bold=True) +
           yellow(command, bold=True) +
           red(" ->", bold=True))


@task
def run(command, show=True):
    """
    Runs a shell comand on the remote server.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _run(command)


@task
def sudo(command, show=True):
    """
    Runs a command as sudo.
    """
    if show:
        print_command(command)
    with hide("running"):
        return _sudo(command)


def log_call(func):
    @wraps(func)
    def logged(*args, **kawrgs):
        header = "-" * len(func.__name__)
        _print(green("\n".join([header, func.__name__, header]), bold=True))
        return func(*args, **kawrgs)
    return logged


def get_templates():
    """
    Returns each of the templates with env vars injected.
    """
    injected = {}
    for name, data in templates.items():
        injected[name] = dict([(k, v % env) for k, v in data.items()])
    return injected


def upload_template_and_reload(name):
    """
    Uploads a template only if it has changed, and if so, reload a
    related service.
    """
    template = get_templates()[name]
    local_path = template["local_path"]
    remote_path = template["remote_path"]
    reload_command = template.get("reload_command")
    owner = template.get("owner")
    mode = template.get("mode")
    remote_data = ""
    if exists(remote_path):
        with hide("stdout"):
            remote_data = sudo("cat %s" % remote_path, show=False)
    with open(local_path, "r") as f:
        local_data = f.read()
        # Escape all non-string-formatting-placeholder occurrences of '%':
        local_data = re.sub(r"%(?!\(\w+\)s)", "%%", local_data)
        if "%(db_pass)s" in local_data:
            env.db_pass = db_pass()
        local_data %= env
    clean = lambda s: s.replace("\n", "").replace("\r", "").strip()
    if clean(remote_data) == clean(local_data):
        return

    upload_template(local_path, remote_path, env, use_sudo=True, backup=False)
    if owner:
        sudo("chown %s %s" % (owner, remote_path))
    if mode:
        sudo("chmod %s %s" % (mode, remote_path))
    if reload_command:
        sudo(reload_command)


def db_pass():
    """
    Prompts for the database password if unknown.
    """
    if not env.db_pass:
        env.db_pass = getpass("Enter the database password: ")
    return env.db_pass


@task
def apt(packages):
    """
    Installs one or more system packages via apt.
    """
    return sudo("apt-get install -y -q " + packages)


@task
def pip(packages):
    """
    Installs one or more Python packages within the virtual environment.
    """
    with virtualenv():
        return sudo("pip3.3 install %s" % packages)


def postgres(command):
    """
    Runs the given command as the postgres user.
    """
    show = not command.startswith("psql")
    return run("sudo -u root sudo -u postgres %s" % command, show=show)


@task
def psql(sql, show=True, withUser=False):
    """
    Runs SQL against the project's database.
    """
    if not withUser:
        out = postgres('psql -c "%s"' % sql)
    else:
        out = postgres('psql -d %s -c "%s"' % (env.proj_name, sql))
    if show:
        print_command(sql)
    return out


@task
def backup(filename):
    """
    Backs up the database.
    """
    return postgres("pg_dump -Fc %s > %s" % (env.proj_name, filename))


@task
def restore(filename):
    """
    Restores the database.
    """
    return postgres("pg_restore -c -d %s %s" % (env.proj_name, filename))


@task
def python(code, show=True):
    """
    Runs Python code in the project's virtual environment, with Django loaded.
    """
    setup = "import os; os.environ[\'DJANGO_SETTINGS_MODULE\']=\'buddyup.settings\';"
    full_code = 'python -c "%s%s"' % (setup, code.replace("`", "\\\`"))
    with project():
        result = run(full_code, show=False)
        if show:
            print_command(code)
    return result


def static():
    """
    Returns the live STATIC_ROOT directory.
    """
    return python("from django.conf import settings;"
                  "print(settings.STATIC_ROOT)").split("\n")[-1]


@task
def manage(command):
    """
    Runs a Django management command.
    """
    return run("%s %s" % (env.manage, command))


#########################
# Install and configure #
#########################

@task
@log_call
def install():
    """
    Installs the base system and Python requirements for the entire server.
    """
    locale = "LC_ALL=%s" % env.locale
    with hide("stdout"):
        if locale not in sudo("cat /etc/default/locale"):
            sudo("update-locale %s" % locale)
            run("exit")
    sudo("apt-get update -y -q")
    apt("nginx python-dev python-setuptools git-core "
        "postgresql libpq-dev memcached supervisor make g++ libbz2-dev")

    sudo("easy_install pip")
    sudo("pip install virtualenv")
    sudo("mkdir -p %s" % env.python_dir)
    sudo("chown %s %s" % (env.user, env.python_dir))

    bzipDir = "%s/bzip2" % env.venv_home
    # install bz2
    sudo("mkdir -p %s" % bzipDir)
    with cd(bzipDir):
        wget("http://bzip.org/1.0.6/bzip2-1.0.6.tar.gz")
        sudo("tar zxvf bzip2-1.0.6.tar.gz")
        with cd("bzip2-1.0.6"):
            sudo(" make -f Makefile-libbz2_so")
            sudo("make")
            sudo("make install")

    # install python
    with cd("%s" % env.python_dir):
        sudo("wget -r -nH --cut-dirs=999 http://www.python.org/ftp/python/3.3.5/Python-3.3.5.tar.xz")
        sudo("tar xJf ./Python-3.3.5.tar.xz")
        with cd("Python-3.3.5"):
            sudo("./configure --prefix=%s --with-bz2=/usr/local/include" % env.python_dir)
            sudo("make && sudo make install")

    sudo("apt-get install binutils libproj-dev libpq-dev postgresql-server-dev-9.3 libgeos-dev")
    sudo("apt-get install python-software-properties libxml2-dev")

    # install GDAL
    sudo("mkdir -p %s/gdal" % env.venv_home)
    with cd("%s/gdal" % env.venv_home):
        sudo("wget -r -nH --cut-dirs=999 http://download.osgeo.org/gdal/1.10.1/gdal-1.10.1.tar.gz")
        sudo("tar xzf gdal-1.10.1.tar.gz")
        with cd("gdal-1.10.1"):
            sudo("./configure")
            sudo("make")
            sudo("make install")

    #install postgis - takes at least 20 minutes
    sudo("mkdir -p %s/postgis" % env.venv_home)
    with cd("%s/postgis" % env.venv_home):
        sudo("wget -r -nH --cut-dirs=999 http://download.osgeo.org/postgis/source/postgis-2.1.2.tar.gz")
        sudo("tar xzf postgis-2.1.2.tar.gz")
        with cd("postgis-2.1.2"):
            sudo("./configure --with-pgconfig=/usr/bin/pg_config")
            sudo("make")
            sudo("make install")

    with cd("%s/postgis/postgis-2.1.2/extensions/postgis" % env.venv_home):
        sudo("make clean")
        sudo("make")
        sudo("make install")

    with cd("%s/postgis/postgis-2.1.2/extensions/postgis_topology" % env.venv_home):
        sudo("make clean")
        sudo("make")
        sudo("make install")

    sudo("ldconfig")
    #


@task
@log_call
def create():
    """
    Create a new virtual environment for a project.
    Pulls the project's repo from version control, adds system-level
    configs for the project, and initialises the database with the
    live host.
    """

    # Create virtualenv
    sudo("mkdir -p %s" % env.venv_home, True)
    sudo("chown %s %s" % (env.user, env.venv_home), True)
    sudo("chown -R %s %s" % (env.user, env.python_dir), True
    )
    #sudo("chown -R %s /home/ubuntu/bin" % env.user, True)
    with cd(env.venv_home):
        if exists(env.proj_name):
            prompt = raw_input("\nVirtualenv exists: %s\nWould you like to replace it? (yes/no) " % env.proj_name)
            if prompt.lower() != "yes":
                print("\nAborting!")
                return False
            remove()
        run("virtualenv %s -p %s/bin/python3.3" % (env.proj_name, env.python_dir))
        vcs = "git" if env.git else "hg"
        run("%s clone %s %s" % (vcs, env.repo_url, env.proj_path))

    # Create DB and DB user.

    pw = db_pass()
    user_sql_args = (env.proj_name, pw.replace("'", "\'"))
    with warn_only():
        user_sql = "CREATE USER %s WITH ENCRYPTED PASSWORD '%s';" % user_sql_args
        psql(user_sql, show=False)
        psql("ALTER USER %s CREATEDB;" % env.proj_name)
        psql("ALTER USER %s SUPERUSER;" % env.proj_name)
    shadowed = "*" * len(pw)
    print_command(user_sql.replace("'%s'" % pw, "'%s'" % shadowed))

    #postgres("createuser --createdb %s;" % env.proj_name)
    #postgres("createdb %s;" % env.proj_name)
    with warn_only():
        psql("CREATE DATABASE %s WITH OWNER %s ENCODING = 'UTF8' "
            "LC_CTYPE = '%s' LC_COLLATE = '%s' TEMPLATE template0;" %
            (env.proj_name, env.proj_name, env.locale, env.locale))
        psql("CREATE EXTENSION postgis;" , True, True)
        psql("CREATE EXTENSION postgis_topology;", True, True)

    #
    # # Set up SSL certificate.
    # conf_path = "/etc/nginx/conf"
    # if not exists(conf_path):
    #     sudo("mkdir %s" % conf_path)
    # with cd(conf_path):
    #     crt_file = env.proj_name + ".crt"
    #     key_file = env.proj_name + ".key"
    #     if not exists(crt_file) and not exists(key_file):
    #         try:
    #             crt_local, = glob(os.path.join("deploy", "*.crt"))
    #             key_local, = glob(os.path.join("deploy", "*.key"))
    #         except ValueError:
    #             parts = (crt_file, key_file, env.live_host)
    #             sudo("openssl req -new -x509 -nodes -out %s -keyout %s "
    #                  "-subj '/CN=%s' -days 3650" % parts)
    #         else:
    #             upload_template(crt_local, crt_file, use_sudo=True)
    #             upload_template(key_local, key_file, use_sudo=True)
    #
    # Set up project.
    upload_template_and_reload("settings")
    with project():
        if env.reqs_path:
            pip("setuptools")
            pip("-r %s/%s --allow-all-external" % (env.proj_path, env.reqs_path))
        pip("gunicorn setproctitle south psycopg2 python3-memcached")
        manage("syncdb --noinput")
        manage("migrate --noinput")
        #python("from django.conf import settings;"
         #      "from django.contrib.sites.models import Site;"
          #     "site, _ = Site.objects.get_or_create(id=settings.SITE_ID);"
           #    "site.domain = '" + env.live_host + "';"
            #   "site.save();")
            #shadowed = "*" * len(pw)
            #print_command(user_py.replace("'%s'" % pw, "'%s'" % shadowed))

    sudo("mkdir -p %s/logs" % env.venv_path)
    sudo("touch %s/logs/gunicorn_supervisor.log" % env.venv_path)

    return True


@task
@log_call
def remove():
    """
    Blow away the current project.
    """
    with warn_only():
        if exists(env.venv_path):
            sudo("rm -rf %s" % env.venv_path)
        for template in get_templates().values():
            remote_path = template["remote_path"]
            if exists(remote_path):
                sudo("rm %s" % remote_path)
        psql("DROP DATABASE %s;" % env.proj_name)
        psql("DROP DATABASE test_%s;" % env.proj_name)
        psql("DROP USER %s;" % env.proj_name)


@task
@log_call
def load_sample_data():
    """
    Load the sample data from the data/folder
    """
    #manage("load_dummy_rules")
    #manage("load_litigantgroups ../data/sample_litigant_group.csv")
    #manage("load_questions ../data/sample_questions.csv")
    #manage("load_questionoptions ../data/sample_question_options.csv")
    #manage("load_litigantgroupquestionfilters ../data/sample_litigant_group_question_filters.csv")
    #manage("load_litigantgroupquestions ../data/sample_litigant_group_questions.csv")
    #manage("load_warrants ../data/warrant_sample_data.csv")


##############
# Deployment #
##############

@task
@log_call
def restart():
    """
    Restart gunicorn worker processes for the project.
    """
    with cd(env.venv_path):
        pid_path = "%s/gunicorn.pid" % env.proj_path
        if exists(pid_path):
            #sudo("kill -HUP `cat %s`" % pid_path)
            sudo("supervisorctl restart gunicorn_%s" % env.proj_name)
        else:
            sudo("supervisorctl start gunicorn_%s" % env.proj_name)


@task
@log_call
def deploy():
    """
    Deploy latest version of the project.
    Check out the latest version of the project from version
    control, install new requirements, sync and migrate the database,
    collect any new static assets, and restart gunicorn's work
    processes for the project.
    """
    if not exists(env.venv_path):
        prompt = raw_input("\nVirtualenv doesn't exist: %s\nWould you like "
                           "to create it? (yes/no) " % env.proj_name)
        if prompt.lower() != "yes":
            print("\nAborting!")
            return False
        create()
    for name in get_templates():
        upload_template_and_reload(name)
    with project():
        backup("last.db")
        static_dir = static()
        if exists(static_dir):
            run("tar -cf last.tar %s" % static_dir)
        git = env.git
        last_commit = "git rev-parse HEAD" if git else "hg id -i"
        run("%s > last.commit" % last_commit)
        with update_changed_requirements():
            run("git pull origin master -f" if git else "hg pull && hg up -C")
        manage("collectstatic -v 0 --noinput")
        manage("syncdb --noinput")
        manage("migrate --noinput")
    restart()
    return True


@task
@log_call
def rollback():
    """
    Reverts project state to the last deploy.
    When a deploy is performed, the current state of the project is
    backed up. This includes the last commit checked out, the database,
    and all static files. Calling rollback will revert all of these to
    their state prior to the last deploy.
    """
    with project():
        with update_changed_requirements():
            update = "git checkout" if env.git else "hg up -C"
            run("%s `cat last.commit`" % update)
        with cd(os.path.join(static(), "..")):
            run("tar -xf %s" % os.path.join(env.proj_path, "last.tar"))
        restore("last.db")
    restart()


@task
@log_call
def all():
    """
    Installs everything required on a new system and deploy.
    From the base software, up to the deployed project.
    """
    install()
    if create():
        deploy()
