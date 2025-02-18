import pyodbc

def initialize_database():
    # Connection string for SQL Server
    connection_string = r'Driver={ODBC Driver 17 for SQL Server};Server=DESKTOP-RRMVMD9\SQLEXPRESS;Database=HotelManagementSystem;Trusted_Connection=yes;'
    
    try:
        # Establish connection
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Creating Rooms table
        cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Rooms' AND xtype='U')
        CREATE TABLE Rooms (
            room_id INT IDENTITY(1,1) PRIMARY KEY,
            room_type NVARCHAR(50),
            availability BIT,
            price DECIMAL(10, 2)
        )''')

        # Creating Guests table
        cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Guests' AND xtype='U')
        CREATE TABLE Guests (
            guest_id INT IDENTITY(101,1) PRIMARY KEY,
            name NVARCHAR(100),
            phone NVARCHAR(15),
            email NVARCHAR(100)
        )''')

        # Creating Bookings table
        cursor.execute('''
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Bookings' AND xtype='U')
        CREATE TABLE Bookings (
            booking_id INT IDENTITY(1,1) PRIMARY KEY,
            room_id INT,
            guest_id INT,
            check_in DATE,
            check_out DATE,
            FOREIGN KEY (room_id) REFERENCES Rooms(room_id),
            FOREIGN KEY (guest_id) REFERENCES Guests(guest_id)
        )''')

        # Add initial room data for testing
        cursor.execute('''
        IF NOT EXISTS (SELECT * FROM Rooms)
        BEGIN
            INSERT INTO Rooms (room_type, availability, price)
            VALUES
            ('Single', 1, 100.00),
            ('Double', 1, 150.00),
            ('Suite', 1, 250.00),
            ('Single', 1, 90.00);
        END
        ''')

        # Commit changes
        connection.commit()
        print("Database and tables initialized successfully.")
    
    except pyodbc.Error as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Ensure connection is closed
        if connection:
            connection.close()

if __name__ == "__main__":
    initialize_database()
