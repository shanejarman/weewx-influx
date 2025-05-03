# [Databases]

This section lists actual databases. The name of each database is given in
double brackets, for example, `[[archive_sqlite]]`. Each database section
contains the parameters necessary to create and manage the database. The
number of parameters varies depending on the type of database.

## [[archive_sqlite]]

This definition uses the [SQLite](https://sqlite.org/) database engine to
store data. SQLite is open-source, simple, lightweight, highly portable, and
memory efficient. For most purposes it serves nicely.

#### database_type

Set to `SQLite` to signal that this is a SQLite database. The definitions that
go with type `SQLite` are defined in section
[`[DatabaseTypes] / [[SQLite]]`](database-types.md#sqlite).

#### database_name

The path to the SQLite file. If the path is relative, it is relative to
[`SQLITE_ROOT`](database-types.md#sqlite_root). Default is `weewx.sdb`.

#### timeout

How many seconds to wait before raising an error when a table is locked.
Default is `5`.

## [[archive_mysql]]

This definition uses the MySQL database engine to store data. It is free,
highly-scalable, but more complicated to administer.

#### database_type

Set to `MySQL` to signal that this is a MySQL database. The definitions that
go with type `MySQL` are defined in section
[`[DatabaseTypes] / [[MySQL]]`](database-types.md#mysql).

#### database_name

The name of the database. Default is `weewx`.

## [[archive_influxdb]]

This definition uses the InfluxDB database engine to store data. InfluxDB is a purpose-built
time-series database that can be useful for storing and analyzing large amounts of weather data.

#### database_type

Set to `InfluxDB` to signal that this is an InfluxDB database. The definitions that
go with type `InfluxDB` are defined in section
[`[DatabaseTypes] / [[InfluxDB]]`](database-types.md#influxdb).

#### bucket

The InfluxDB bucket name to use. This is equivalent to a database name in traditional 
SQL databases. Required.

