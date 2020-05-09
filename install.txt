This File is Made By Divyesh Ransariya on 19 Feb, 2020 
for own Purpose.
Please follow step by step to configure airflow with MySQL As Backend.
AirFlow Installation

Requirements
	Python2.7 or Python 3.6 later
		    // Checking python version
    			$ python -V  or $python3 -V
    		   // On fails Above commands show you error then run belows
			$ yum install python-setuptools
	Pip
		$yum install python-pip
Main Steps

# Set AIRFLOW_HOME environment variable to ~/airflow.
 $export AIRFLOW_HOME=~/airflow  
# Dependencies required for Apache Airflow --> [libmysqlclient-dev, libssl-dev, libkrb5-dev, libsasl2-dev]

# After installing dependencies, Install Airflow and its packages
 $sudo pip3 install apache-airflow
# After successfully installing airflow, we will initialise Airflow’s database
 $ airflow initdb

--------------------------------------------Starting Airflow ---------------------------------------------------
# All the required installation and configuration is done. We will create a dags folder in airflow home directory .i.e;  at /home/ubuntu/airflow location
$ mkdir -p /home/ubuntu/airflow/dags/

# And then we’ll start all airflow services to up airflow webUI
$ airflow webserver

# Make some changes in airflow.cfg file.(~/airflow/arflow.cfg)
port=2222

----------------------------------------SetUp MYSQL For parallel Execution ----------------------------------------
# Before we will install Airflow, please install missing libraries for MySQL client:

$ sudo yum whatprovides libmysqlclient*
# Above command gives you all dependencies for MYSQL client so please ensure that,
# You install before move Further 

# All here is link to install MySQL on Unix machine kindly,
# Go through this if you are new to this --> https://bigdata-etl.com/how-to-install-mysql-database-on-ubutnu-18-04/

# Now we can install Apache Airflow with additional feature [mysql]. 
# It will allow us to use MySQL database as an Airflow storage.
$ export SLUGIFY_USES_TEXT_UNIDECODE=yes && pip install apache-airflow[mysql,crypto]

# During installation you run the command, which created the SQLite database in AIRFLOW_HOME(~/airflow) directory which allows user start journey with Airflow. 
# Of course, it is correct way. You must have the point of start.

# we will install mysql-server package and finally configure our MySQL database instance
$ sudo yum install mysql-server

# Configure MySQL database instance
$ sudo mysql_secure_installation

# When you run the MySQL secure-installation you will follow step by step to configure security of our MySQL database instance. 
# One of the most important step (in my opinion) is to disallow root user to login remotely. 
# If you will disallow it, you will be able to login to MySQL only from local machine when the database was installed. 
# It will give you two levels of authentication. Firstly, you must be logged in remote machine and next you can login to MySQL database

# Now its Time to Change authentication method
1. Login to MySQL database. (mysql> sudo mysql)
2. Check current authentication methods for each user.(mysql> SELECT user, plugin FROM mysql.user;)
3. Set new passwordfor root.(mysql> ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'my_new_strong_password';)
# If setp 3 Shows you Error like (Password Don't meet policy requirement then you have do some digging!)

	mysql>  SHOW VARIABLES LIKE 'validate_password%';
	+--------------------------------------+--------+
	| Variable_name                        | Value  |
	+--------------------------------------+--------+
	| validate_password.check_user_name    | ON     |
	| validate_password.dictionary_file    |        |
	| validate_password.length             | 8      |
	| validate_password.mixed_case_count   | 1      |
	| validate_password.number_count       | 1      |
	| validate_password.policy             | MEDIUM |
	| validate_password.special_char_count | 1      |
	+--------------------------------------+--------+

# see password policy is MED by default, chnage it to (LOW or HIGH) whatever...
# I prefer low option coz of simplicity
mysql> SET GLOBAL validate_password_policy=LOW;
# Now all set Go back to step 3

4. Flush privileges.(mysql> FLUSH PRIVILEGES;)
5. Verify new status of authentication methods.[See Below]
	
	mysql>  SELECT user, plugin FROM mysql.user;
		+------------------+-----------------------+
		| user             | plugin                |
		+------------------+-----------------------+
		| airflow          | mysql_native_password |
		| mysql.infoschema | caching_sha2_password |
		| mysql.session    | caching_sha2_password |
		| mysql.sys        | caching_sha2_password |
		| root             | mysql_native_password |
		+------------------+-----------------------+
		5 rows in set (0.00 sec)

# Create Airflow database 
mysql> CREATE DATABASE airflow;

# Now create new use and grant all privileges to airflow database for airflow user:

# -- Create "airflow" user
mysql> CREATE USER 'airflow'@'localhost' IDENTIFIED BY 'airflow';

# -- Grant all privileges
mysql> GRANT ALL PRIVILEGES ON airflow. * TO 'airflow'@'localhost';

# -- Flush privileges
mysql> FLUSH PRIVILEGES;

[Make sure You created airflow user in DB]
	mysql> select host, user from mysql.user;
	+-----------+------------------+
	| host      | user             |
	+-----------+------------------+
	| localhost | airflow          |
	| localhost | mysql.infoschema |
	| localhost | mysql.session    |
	| localhost | mysql.sys        |
	| localhost | root             |
	+-----------+------------------+
	5 rows in set (0.00 sec)

# Default initializaion of Airflow SQLite database
$ airflow initdb

-------------------------------- To configure Airflow to manage parallel execution! -------------------------

[Make sure Belows 3 lines you read carefully!]
# First, you must have new storage for Airflow metadata. 
# In our case I will use MySQL database. In this scenario I have already installed MySQL database in the same machine as Airflow, 
# but you can of course use another one which you have instantiated connectivity from Airflow host.

# Now we are going into the main phase of Airflow configuration. 
# Airflow uses the airflow.cfg file where all the configuration parameters are specified. 
# You can find the configuration file in $AIRFLOW_HOME directory. 
# Let’s open it and change executor, sql_alchemy_conn and fernet_key parameters.


1. Chnage executor in airflow.cfg file
#executor = SequentialExecutor
executor = LocalExecutor

2. sql_alchemy_conn:
# sql_alchemy_conn = sqlite:////home/pawel/airflow/airflow.db
sql_alchemy_conn = mysql://airflow:airflow@localhost:3306/airflow

3. fernet_key:
# If you don’t know how to create own Fernet key please follow run $python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# on error for getting run($pip3 install cryptography)
# Replace existing value using new one created by you.
# Secret key to save connection passwords in the db
fernet_key =NH0ZMCJi8k51RfdTkpxYb08MFx2w6FsowSqZIQoF5_o=

# One more MySQL configuration
# Airflow relies on more strict ANSI SQL settings for MySQL in order to have sane defaults. 
# In this case we must specify explicit_defaults_for_timestamp=1 in your my.cnf under [mysqld].

------------------------------------- ALL DONE ---------------------------------------------------------------
# Start the server!
$ airflow webserver 





