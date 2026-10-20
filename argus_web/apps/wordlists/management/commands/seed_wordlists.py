"""Cria as wordlists embutidas do Argus (idempotente)."""
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.wordlists.models import Wordlist

BUILTIN = {
    "api-paths-mini": {
        "kind": Wordlist.KIND_API,
        "description": "Paths minimos de API (1o passe)",
        "content": """\
/swagger.json
/openapi.json
/api-docs
/api
/api/v1
/api/v2
/graphql
/rest
""",
    },
    "api-paths-full": {
        "kind": Wordlist.KIND_API,
        "description": "Conjunto amplo de paths de API",
        "from_file": "wordlists/api_paths.txt",
    },
    "content-common": {
        "kind": Wordlist.KIND_CONTENT,
        "description": "Arquivos e diretorios comuns",
        "content": """\
/admin
/admin/
/login
/logout
/register
/dashboard
/.git/config
/.env
/.env.bak
/robots.txt
/sitemap.xml
/.well-known/security.txt
/backup
/backup.zip
/config
/debug
/status
/health
/metrics
/phpinfo.php
""",
    },
    "params-common": {
        "kind": Wordlist.KIND_PARAMS,
        "description": "Nomes comuns de parametros",
        "content": """\
id
user
username
email
password
token
api_key
apikey
key
secret
debug
test
admin
role
file
path
url
redirect
next
callback
page
limit
offset
sort
order
filter
q
search
""",
    },
    "useragents-top": {
        "kind": Wordlist.KIND_USERAGENT,
        "description": "User-Agents comuns para rotacao",
        "content": """\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15
""",
    },
}


class Command(BaseCommand):
    help = "Cria/atualiza as wordlists embutidas."

    def handle(self, *args, **opts):
        created = updated = 0
        for name, spec in BUILTIN.items():
            content = spec.get("content", "")
            if spec.get("from_file"):
                p = Path(spec["from_file"])
                if p.exists():
                    content = p.read_text(encoding="utf-8")
                else:
                    self.stdout.write(
                        f"  [skip] {spec['from_file']} nao existe")

            obj, is_new = Wordlist.objects.update_or_create(
                owner=None, name=name,
                defaults={
                    "kind": spec["kind"],
                    "description": spec["description"],
                    "content": content,
                    "is_builtin": True,
                },
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"wordlists: {created} criadas, {updated} atualizadas"))
