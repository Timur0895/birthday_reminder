import gspread
from oauth2client.service_account import ServiceAccountCredentials

def get_birthdays_data():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)

    spreadsheet = client.open('AdAccounts')  # Замени на своё название
    sheet = spreadsheet.worksheet('Birthdays')  # Название листа

    return sheet.get_all_records()

