"""Merging two head revisions

Revision ID: 424ed97e693
Revises: 39fc43a77e8, 3cc3881f524
Create Date: 2015-08-10 23:04:12.455185

"""

# revision identifiers, used by Alembic.
revision = '424ed97e693'
down_revision = ('39fc43a77e8', '3cc3881f524')
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

