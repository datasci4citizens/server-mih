from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Skeleton management command: placeholder for user migration if needed'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Do not write to DB')

    def handle(self, *args, **options):
        dry = options.get('dry_run')
        if dry:
            self.stdout.write('Dry run: no changes will be made')
        # This is intentionally a skeleton — no source DB configured since no real data.
        self.stdout.write(self.style.SUCCESS('migrate_users_skeleton executed (no-op)'))
