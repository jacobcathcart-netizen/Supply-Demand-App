import snowflake.connector

conn = snowflake.connector.connect(
    user="JACOB.CATHCART@CCRENEW.COM",
    account="ONIYJML-CCR_PRD",
    authenticator="externalbrowser",
    warehouse="SA_COMPUTE_WH",
    database="SA",
    role="SA_OWNER",
)

cur = conn.cursor()
try:
    cur.execute("select current_user(), current_role(), current_warehouse()")
    print(cur.fetchone())
finally:
    cur.close()
    conn.close()
    
    
    
    
    