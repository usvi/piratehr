#/bin/bash

# Give table main dir as parameter.
# Create database with this if necessary:
# mysqladmin --default-character-set=utf8 -p create PirateWeb

QUERIES_SUBDIR="Queries"
FULLTABLES_SUBDIR="FullTables"

if [ ! -d "$1" -o  ! -d "$1/$QUERIES_SUBDIR"  -o  ! -d "$1/$FULLTABLES_SUBDIR"  ]; then
    echo "Error: No valid base directory given."
    echo "Give base directory of SQL files as first argument."
    exit 1
fi

echo "Give SQL password"
read sql_password

mysql -p$sql_password < $1/$QUERIES_SUBDIR/Schema\ for\ queries.sql PirateWeb
mysql -p$sql_password < $1/$QUERIES_SUBDIR/People.sql PirateWeb
mysql -p$sql_password < $1/$QUERIES_SUBDIR/PeopleRoles.sql PirateWeb
mysql -p$sql_password < $1/$QUERIES_SUBDIR/Memberships.sql PirateWeb
mysql -p$sql_password < $1/$QUERIES_SUBDIR/MembershipPayments.sql PirateWeb
mysql -p$sql_password < $1/$QUERIES_SUBDIR/Activists.sql PirateWeb
mysql -p$sql_password < $1/$QUERIES_SUBDIR/ObjectOptionalData.sql PirateWeb

mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/Cities2012-08-08\ 21-44-09.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/Countries2012-08-08\ 21-44-13.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/Geographies2012-08-08\ 21-44-13.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/ObjectOptionalDataTypes2012-08-08\ 21-44-14.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/ObjectTypes2012-08-08\ 21-44-14.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/Organizations2012-08-08\ 21-44-15.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/OrganizationUptakeGeographies2012-08-08\ 21-44-15.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/PersonRoleTypes2012-08-08\ 21-44-16.sql
mysql -p$sql_password < $1/$FULLTABLES_SUBDIR/PostalCodes2012-08-08\ 21-44-16.sql
