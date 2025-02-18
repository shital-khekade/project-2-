import wx
import pyodbc
from datetime import datetime
import re

# Connection string for SQL Server
connection_string = r'Driver={ODBC Driver 17 for SQL Server};Server=DESKTOP-RRMVMD9\SQLEXPRESS;Database=HotelManagementSystem;Trusted_Connection=yes;'

# Validation functions
def validate_email(email):
    """Validate email format."""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email)

def validate_phone(phone):
    """Validate phone number (numeric, reasonable length)."""
    return phone.isdigit() and 7 <= len(phone) <= 15

def validate_date(date_str):
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

# Function to fetch available rooms
def fetch_available_rooms():
    try:
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        cursor.execute('''
            SELECT r.room_id, r.room_type, r.price
            FROM Rooms r
            WHERE NOT EXISTS (
                SELECT 1
                FROM Bookings b
                WHERE b.room_id = r.room_id
                AND GETDATE() BETWEEN b.check_in AND b.check_out
            )
        ''')
        rooms = cursor.fetchall()
        # Convert rows to a list of dictionaries
        room_list = [{"room_id": row.room_id, "room_type": row.room_type, "price": row.price} for row in rooms]
        return room_list
    except pyodbc.Error as e:
        wx.MessageBox(f"Database error: {e}", "Error", wx.OK | wx.ICON_ERROR)
        return []
    finally:
        if 'connection' in locals():
            connection.close()

# Function to book a room
def book_room(room_id, guest_name, guest_phone, guest_email, check_in, check_out):
    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

        if check_in_date >= check_out_date:
            wx.MessageBox("Check-out date must be after check-in date.", "Error", wx.OK | wx.ICON_WARNING)
            return

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check for overlapping bookings
        cursor.execute('''
            SELECT 1
            FROM Bookings
            WHERE room_id = ? AND (
                ? BETWEEN check_in AND check_out OR
                ? BETWEEN check_in AND check_out OR
                check_in BETWEEN ? AND ?
            )
        ''', (room_id, check_in_date, check_out_date, check_in_date, check_out_date))
        overlapping_booking = cursor.fetchone()

        if overlapping_booking:
            wx.MessageBox("Room is not available for the selected dates.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        # Insert guest information
        cursor.execute('INSERT INTO Guests (name, phone, email) VALUES (?, ?, ?)', (guest_name, guest_phone, guest_email))
        cursor.execute('SELECT SCOPE_IDENTITY()')
        guest_id = cursor.fetchone()[0]

        # Insert booking information
        cursor.execute('INSERT INTO Bookings (room_id, guest_id, check_in, check_out) OUTPUT INSERTED.booking_id VALUES (?, ?, ?, ?)', 
                       (room_id, guest_id, check_in_date, check_out_date))
        booking_id = cursor.fetchone()[0]
        connection.commit()

        wx.MessageBox(f"Room booked successfully! Your Booking ID is {booking_id}.", "Success", wx.OK | wx.ICON_INFORMATION)

    except Exception as e:
        wx.MessageBox(f"Error: {e}", "Error", wx.OK | wx.ICON_ERROR)
    finally:
        if 'connection' in locals():
            connection.close()

# Function to cancel a booking
def cancel_booking(booking_id):
    try:
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Check if the booking exists
        cursor.execute('SELECT * FROM Bookings WHERE booking_id = ?', (booking_id,))
        booking = cursor.fetchone()

        if not booking:
            wx.MessageBox("No booking found with the given Booking ID.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        # Delete the booking
        cursor.execute('DELETE FROM Bookings WHERE booking_id = ?', (booking_id,))
        connection.commit()

        wx.MessageBox(f"Booking with ID {booking_id} has been successfully canceled.", "Success", wx.OK | wx.ICON_INFORMATION)
    except pyodbc.Error as e:
        wx.MessageBox(f"Database error: {e}", "Error", wx.OK | wx.ICON_ERROR)
    finally:
        if 'connection' in locals():
            connection.close()

# Function to view booking details
def view_booking(booking_id):
    try:
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        # Query to fetch booking details based on Booking ID
        cursor.execute('''
            SELECT  rooms.*, guests.*, bookings.* 
            FROM  rooms LEFT JOIN  bookings ON rooms.room_id = bookings.room_id
            LEFT JOIN  guests ON guests.guest_id = bookings.guest_id
            WHERE bookings.booking_id = ?
        ''', (booking_id,))
        booking = cursor.fetchone()

        if booking:
            booking_details = (
                f"Booking ID: {booking.booking_id}\n"
                f"Room ID: {booking.room_id}\n"
                f"Room Type: {booking.room_type}\n"
                f"Check-in Date: {booking.check_in}\n"
                f"Check-out Date: {booking.check_out}\n"
                f"Guest Name: {booking.name}\n"
                f"Guest Email: {booking.email}\n"
                f"Guest Phone: {booking.phone}"
            )
            wx.MessageBox(booking_details, "Booking Details", wx.OK | wx.ICON_INFORMATION)
        else:
            wx.MessageBox(f"No details found for Booking ID: {booking_id}", "Info", wx.OK | wx.ICON_INFORMATION)
    except pyodbc.Error as e:
        wx.MessageBox(f"Database error: {e}", "Error", wx.OK | wx.ICON_ERROR)
    finally:
        if 'connection' in locals():
            connection.close()

# GUI Application
class BookingApp(wx.App):
    def OnInit(self):
        self.frame = wx.Frame(None, title="Hotel Booking System", size=(600, 400))
        panel = wx.Panel(self.frame)

        # Layout using BoxSizer
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Buttons for functionalities
        self.view_rooms_button = wx.Button(panel, label="View Available Rooms")
        self.book_room_button = wx.Button(panel, label="Book Room")
        self.cancel_booking_button = wx.Button(panel, label="Cancel Booking")
        self.view_booking_button = wx.Button(panel, label="View Booking")

        # Add tooltips for accessibility
        self.view_rooms_button.SetToolTip("Click to view all available rooms")
        self.book_room_button.SetToolTip("Click to book a room")
        self.cancel_booking_button.SetToolTip("Click to cancel an existing booking")
        self.view_booking_button.SetToolTip("Click to view details of a booking")

        # Add buttons to sizer
        vbox.Add(self.view_rooms_button, flag=wx.EXPAND | wx.ALL, border=10)
        vbox.Add(self.book_room_button, flag=wx.EXPAND | wx.ALL, border=10)
        vbox.Add(self.cancel_booking_button, flag=wx.EXPAND | wx.ALL, border=10)
        vbox.Add(self.view_booking_button, flag=wx.EXPAND | wx.ALL, border=10)

        panel.SetSizer(vbox)

        # Bind buttons to event handlers
        self.view_rooms_button.Bind(wx.EVT_BUTTON, self.on_view_rooms)
        self.book_room_button.Bind(wx.EVT_BUTTON, self.on_book_room)
        self.cancel_booking_button.Bind(wx.EVT_BUTTON, self.on_cancel_booking)
        self.view_booking_button.Bind(wx.EVT_BUTTON, self.on_view_booking)

        self.frame.Show()
        return True

    def on_view_rooms(self, event):
        rooms = fetch_available_rooms()
        if not rooms:
            wx.MessageBox("No rooms available.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        available_rooms = "\n".join([f"ID: {room['room_id']}, Type: {room['room_type']}, Price: {room['price']}" for room in rooms])
        wx.MessageBox(available_rooms, "Available Rooms", wx.OK | wx.ICON_INFORMATION)

    def on_book_room(self, event):
        rooms = fetch_available_rooms()
        if not rooms:
            wx.MessageBox("No rooms available for booking.", "Info", wx.OK | wx.ICON_INFORMATION)
            return

        dialog = BookingFormDialog(self.frame, rooms)
        dialog.ShowModal()
        dialog.Destroy()

    def on_cancel_booking(self, event):
        dialog = wx.TextEntryDialog(None, "Enter Booking ID to cancel:", "Cancel Booking")
        if dialog.ShowModal() == wx.ID_OK:
            booking_id = dialog.GetValue()
            if booking_id.isdigit():
                cancel_booking(int(booking_id))
            else:
                wx.MessageBox("Booking ID must be a numeric value.", "Error", wx.OK | wx.ICON_ERROR)

    def on_view_booking(self, event):
        dialog = wx.TextEntryDialog(None, "Enter Booking ID to view details:", "View Booking")
        if dialog.ShowModal() == wx.ID_OK:
            booking_id = dialog.GetValue()
            if booking_id.isdigit():
                view_booking(int(booking_id))
            else:
                wx.MessageBox("Booking ID must be a numeric value.", "Error", wx.OK | wx.ICON_ERROR)

class BookingFormDialog(wx.Dialog):
    def __init__(self, parent, rooms):
        super().__init__(parent, title="Book a Room", size=(400, 500))
        panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)

        # Room selection
        vbox.Add(wx.StaticText(panel, label="Select Room:"), flag=wx.LEFT | wx.TOP, border=10)
        self.room_choice = wx.Choice(panel, choices=[f"ID: {room['room_id']}, Type: {room['room_type']}, Price: {room['price']}" for room in rooms])
        vbox.Add(self.room_choice, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # Guest details
        fields = [("Enter your Name:", "name_input"), ("Enter your Phone Number:", "phone_input"),
                  ("Enter your Email Address:", "email_input"), ("Check-in Date (YYYY-MM-DD):", "check_in_input"),
                  ("Check-out Date (YYYY-MM-DD):", "check_out_input")]
        for label, attr in fields:
            vbox.Add(wx.StaticText(panel, label=label), flag=wx.LEFT | wx.TOP, border=10)
            setattr(self, attr, wx.TextCtrl(panel))
            vbox.Add(getattr(self, attr), flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)

        # Submit button
        self.submit_button = wx.Button(panel, label="Book Room")
        vbox.Add(self.submit_button, flag=wx.CENTER | wx.ALL, border=10)

        self.submit_button.Bind(wx.EVT_BUTTON, self.on_submit)
        panel.SetSizer(vbox)

        self.rooms = rooms

    def on_submit(self, event):
        selected_room_index = self.room_choice.GetSelection()
        if selected_room_index == wx.NOT_FOUND:
            wx.MessageBox("Please select a room.", "Error", wx.OK | wx.ICON_ERROR)
            return

        room_id = self.rooms[selected_room_index]['room_id']
        guest_name = self.name_input.GetValue()
        guest_phone = self.phone_input.GetValue()
        guest_email = self.email_input.GetValue()
        check_in = self.check_in_input.GetValue()
        check_out = self.check_out_input.GetValue()

        if not all([guest_name, guest_phone, guest_email, check_in, check_out]):
            wx.MessageBox("All fields are required.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if not validate_email(guest_email):
            wx.MessageBox("Invalid email format.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if not validate_phone(guest_phone):
            wx.MessageBox("Invalid phone number. Please enter a numeric value with 7 to 15 digits.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if not validate_date(check_in) or not validate_date(check_out):
            wx.MessageBox("Invalid date format. Use YYYY-MM-DD.", "Error", wx.OK | wx.ICON_ERROR)
            return

        book_room(room_id, guest_name, guest_phone, guest_email, check_in, check_out)
        self.Close()

if __name__ == "__main__":
    app = BookingApp(False)
    app.MainLoop()
