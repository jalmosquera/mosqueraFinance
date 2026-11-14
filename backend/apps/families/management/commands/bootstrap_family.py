from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.families.bootstrap import bootstrap_jalberth


class Command(BaseCommand):
    help = "Create the initial Jalberth account, family, and administrator membership."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--family-name", required=True)
        parser.add_argument("--password")
        parser.add_argument("--noinput", action="store_true")

    def handle(self, *args, **options):
        password = options["password"]
        if password is None and not options["noinput"]:
            password = getpass("Initial Jalberth password: ")
        if not password:
            raise CommandError("Provide --password when using --noinput.")
        try:
            user, family, membership = bootstrap_jalberth(
                email=options["email"], password=password, family_name=options["family_name"]
            )
        except Exception as error:
            raise CommandError(str(error)) from error
        self.stdout.write(
            self.style.SUCCESS(
                f"Created family {family.pk}, Jalberth user {user.pk}, and membership {membership.pk}."
            )
        )
