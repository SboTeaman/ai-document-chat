import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collections', '0001_initial'),
        ('search', '0001_initial'),
    ]

    operations = [
        # The initial migration stored the collection as a bare BigIntegerField;
        # the model now declares a proper FK. Replace the raw column with a real
        # foreign key (same collection_id column name, now with a constraint).
        migrations.RemoveField(
            model_name='searchquery',
            name='collection_id',
        ),
        migrations.AddField(
            model_name='searchquery',
            name='collection',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='search_queries',
                to='collections.collection',
            ),
        ),
    ]
