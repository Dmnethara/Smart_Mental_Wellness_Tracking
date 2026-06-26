import pymysql

def configure_mysql():
    print("Attempting to connect to local MySQL server as root...")
    try:
        # Connect as root with empty password
        conn = pymysql.connect(host='localhost', user='root', password='')
        cursor = conn.cursor()
        
        # Drop and create database
        cursor.execute("DROP DATABASE IF EXISTS mental_wellness_db;")
        cursor.execute("CREATE DATABASE mental_wellness_db;")
        print("Database 'mental_wellness_db' dropped and recreated fresh.")
        
        # Create user and grant privileges
        try:
            cursor.execute("CREATE USER IF NOT EXISTS 'wellness_user'@'localhost' IDENTIFIED BY 'wellness_pass';")
            print("User 'wellness_user' checked/created.")
        except Exception as ue:
            print("Note on user creation:", ue)
            
        cursor.execute("GRANT ALL PRIVILEGES ON mental_wellness_db.* TO 'wellness_user'@'localhost';")
        cursor.execute("FLUSH PRIVILEGES;")
        print("Privileges granted to 'wellness_user'.")
        
        conn.commit()
        conn.close()
        print("MySQL configuration completed successfully!")
        return True
    except Exception as e:
        print("Failed to configure MySQL as root with empty password. Error:", e)
        return False

if __name__ == "__main__":
    configure_mysql()
