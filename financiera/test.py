import mysql.connector
conn = mysql.connector.connect(
    host='127.0.0.1',
    port=3307,
    user='root',
    password='mysqldb',
    database='PAG'
)
print(conn.is_connected())
