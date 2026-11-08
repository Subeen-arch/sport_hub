"""Create SportHub's isolated development PostgreSQL cluster; never open legacy DBs."""
from pathlib import Path
import os
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / '.runtime'
BIN = ROOT / '.tools' / 'pgsql' / 'bin'
DATA = RUNTIME / 'postgres'
ENV = ROOT / 'backend' / '.env'


def run(*args):
    subprocess.run([str(x) for x in args], check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)


def main():
    if not (BIN / 'initdb.exe').exists():
        sys.exit('Install PostgreSQL Windows binaries into .tools/pgsql first.')
    if ENV.exists() or DATA.exists():
        sys.exit('Existing new environment detected. Refusing to overwrite it. Use scripts/start.ps1.')
    RUNTIME.mkdir(exist_ok=True)
    (ROOT / 'backend').mkdir(exist_ok=True)
    admin_password, app_password = secrets.token_urlsafe(36), secrets.token_urlsafe(36)
    pwfile = RUNTIME / 'init-password.txt'
    pwfile.write_text(admin_password, encoding='utf-8')
    try:
        run(BIN / 'initdb.exe', '-D', DATA, '-U', 'sporthub_admin', '--pwfile', pwfile,
            '--auth=scram-sha-256', '--encoding=UTF8', '--locale=C')
    finally:
        pwfile.unlink(missing_ok=True)
    with (DATA / 'postgresql.conf').open('a', encoding='utf-8') as f:
        f.write("\nlisten_addresses = '127.0.0.1'\nport = 55432\n")
    run(BIN / 'pg_ctl.exe', '-D', DATA, '-l', RUNTIME / 'postgres.log', '-w', 'start')
    import psycopg
    from psycopg import sql
    with psycopg.connect(host='127.0.0.1', port=55432, dbname='postgres',
                         user='sporthub_admin', password=admin_password, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE ROLE sporthub_app LOGIN CREATEDB PASSWORD {}').format(sql.Literal(app_password)))
        conn.execute('CREATE DATABASE sporthub_next OWNER sporthub_app')
    ENV.write_text(
        'DJANGO_SECRET_KEY=' + secrets.token_urlsafe(64) + '\n'
        'DJANGO_DEBUG=True\n'
        'DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,testserver\n'
        'DATABASE_URL=postgresql://sporthub_app:' + app_password + '@127.0.0.1:55432/sporthub_next\n'
        'POSTGRES_DB=sporthub_next\nPOSTGRES_USER=sporthub_app\nPOSTGRES_PASSWORD=' + app_password + '\n'
        'POSTGRES_HOST=127.0.0.1\nPOSTGRES_PORT=55432\n'
        'FRONTEND_URL=http://localhost:5173\n'
        'DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n'
        'KHALTI_ENV=sandbox\nKHALTI_SECRET_KEY=\n', encoding='utf-8')
    (RUNTIME / 'postgres-admin.env').write_text('PGPASSWORD=' + admin_password + '\n', encoding='utf-8')
    print('Created independent PostgreSQL sporthub_next at 127.0.0.1:55432. Credentials saved privately.')


if __name__ == '__main__':
    main()
