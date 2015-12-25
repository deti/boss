"""Merge branch

Revision ID: 23d8efcd529
Revises: 1802db98d8a, 2b500992762
Create Date: 2015-06-10 15:04:18.709814

"""

# revision identifiers, used by Alembic.
revision = '23d8efcd529'
down_revision = ('1802db98d8a', '2b500992762')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_account():
    pass


def downgrade_account():
    pass


def upgrade_fitter():
    pass


def downgrade_fitter():
    pass

