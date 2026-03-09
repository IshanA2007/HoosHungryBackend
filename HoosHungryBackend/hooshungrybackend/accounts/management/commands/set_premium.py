from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Grant or revoke premium membership for a user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument(
            '--revoke',
            action='store_true',
            help='Revoke premium instead of granting it',
        )

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f"User '{username}' does not exist.")

        profile = user.profile
        if options['revoke']:
            profile.premium_member = False
            profile.save()
            self.stdout.write(self.style.SUCCESS(f"Revoked premium from '{username}'."))
        else:
            profile.premium_member = True
            profile.save()
            self.stdout.write(self.style.SUCCESS(f"Granted premium to '{username}'."))
