"""Delete nullable=false for customer

Revision ID: 4c1fcc9a81d
Revises: 4dbaa3104f4
Create Date: 2015-05-28 15:02:25.929790

"""

# revision identifiers, used by Alembic.
revision = '4c1fcc9a81d'
down_revision = '4dbaa3104f4'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_account():
    ### commands auto generated by Alembic - please adjust! ###

    op.alter_column('customer', 'address',
               existing_type=mysql.VARCHAR(length=254),
               nullable=True)
    op.alter_column('customer', 'birthday',
               existing_type=sa.DATE(),
               nullable=True)
    op.alter_column('customer', 'city',
               existing_type=mysql.VARCHAR(length=32),
               nullable=True)
    op.alter_column('customer', 'country',
               existing_type=mysql.VARCHAR(length=32),
               nullable=True)
    op.alter_column('customer', 'name',
               existing_type=mysql.VARCHAR(length=64),
               nullable=True)
    op.alter_column('customer', 'telephone',
               existing_type=mysql.VARCHAR(length=16),
               nullable=True)
    ### end Alembic commands ###


def downgrade_account():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('customer', 'telephone',
               existing_type=mysql.VARCHAR(length=16),
               nullable=False)
    op.alter_column('customer', 'name',
               existing_type=mysql.VARCHAR(length=64),
               nullable=False)
    op.alter_column('customer', 'country',
               existing_type=mysql.VARCHAR(length=32),
               nullable=False)
    op.alter_column('customer', 'city',
               existing_type=mysql.VARCHAR(length=32),
               nullable=False)
    op.alter_column('customer', 'birthday',
               existing_type=sa.DATE(),
               nullable=False)
    op.alter_column('customer', 'address',
               existing_type=mysql.VARCHAR(length=254),
               nullable=False)
    ### end Alembic commands ###


def upgrade_fitter():
    pass


def downgrade_fitter():
    pass

