import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import datetime
import json

class SheetManager:
    def __init__(self, credentials_json_content, sheet_url):
        self.scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Determine if credentials are a file path or a JSON string
        if os.path.exists(credentials_json_content):
             self.creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_json_content, self.scope)
        else:
             # Assume JSON string (for GitHub Secrets)
             creds_dict = json.loads(credentials_json_content)
             self.creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, self.scope)

        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_url(sheet_url)
        
        # Ensure tabs exist
        self.leads_worksheet = self._get_or_create_worksheet("Leads", ["Company", "State", "City", "Niche", "Email", "Website", "Instagram", "Facebook", "LinkedIn", "Source", "Date"])
        self.email_worksheet = self._get_or_create_worksheet("Leads with Email", ["Email", "Company", "State", "City", "Niche", "Primary Mail", "Follow Up 1", "Follow Up 2", "Follow Up 3", "Follow Up 4", "Follow Up 5", "Date Added"])
        self.status_worksheet = self._get_or_create_worksheet("Status", ["Key", "Value", "Last Updated"])
        
        # Initialize Status if empty
        if not self.status_worksheet.get_all_values()[1:]:
             self.status_worksheet.append_row(["Last Niche", "", str(datetime.date.today())])
             self.status_worksheet.append_row(["Last State", "", str(datetime.date.today())])
             self.status_worksheet.append_row(["Last City", "", str(datetime.date.today())])
             self.status_worksheet.append_row(["Leads Found Today", "0", str(datetime.date.today())])
             self.status_worksheet.append_row(["Run Date", str(datetime.date.today()), str(datetime.date.today())])

    def _get_or_create_worksheet(self, title, headers):
        try:
            ws = self.sheet.worksheet(title)
        except gspread.exceptions.WorksheetNotFound:
            ws = self.sheet.add_worksheet(title=title, rows=1000, cols=20)
            ws.append_row(headers)
        return ws

    def get_status(self):
        """Reads the current state from the Status sheet."""
        data = self.status_worksheet.get_all_records()
        status = {row['Key']: row['Value'] for row in data}
        
        # Reset counter if new day
        last_run = status.get("Run Date")
        today = str(datetime.date.today())
        
        if last_run != today:
             print(f"[State] New day detected ({today}). Resetting counter.")
             self.update_status("Leads Found Today", 0)
             self.update_status("Run Date", today)
             status["Leads Found Today"] = 0
             status["Run Date"] = today
             
        return status

    def update_status(self, key, value):
        """Updates a specific key in the Status sheet."""
        # Find cell
        try:
            cell = self.status_worksheet.find(key)
            self.status_worksheet.update_cell(cell.row, 2, str(value))
            self.status_worksheet.update_cell(cell.row, 3, str(datetime.date.today()))
        except:
            # key missing, append
            self.status_worksheet.append_row([key, str(value), str(datetime.date.today())])

    def add_lead(self, lead_data):
        """Appends a lead to the Leads sheet. If it has email, adds to 'Leads with Email' too."""
        today_str = str(datetime.date.today())
        
        # 1. Always add to generic 'Leads' (Archive)
        row = [
            lead_data.get("Company"),
            lead_data.get("State"),
            lead_data.get("City"),
            lead_data.get("Niche"),
            lead_data.get("Email"),
            lead_data.get("Website"),
            lead_data.get("Instagram"),
            lead_data.get("Facebook"),
            lead_data.get("LinkedIn"),
            lead_data.get("Source"),
            today_str
        ]
        self.leads_worksheet.append_row(row)
        
        # 2. If valid email, add to Email Tracking Sheet
        email = lead_data.get("Email")
        if email and "@" in str(email):
            row_email = [
                email,
                lead_data.get("Company"),
                lead_data.get("State"),
                lead_data.get("City"),
                lead_data.get("Niche"),
                "", # Primary Mail
                "", # Follow Up 1
                "", # Follow Up 2
                "", # Follow Up 3
                "", # Follow Up 4
                "", # Follow Up 5
                today_str
            ]
            # Avoid dupes in Email Sheet? Check or just append?
            # Assuming scraper uniqueness check handles logic, just append here
            try:
                self.email_worksheet.append_row(row_email)
            except Exception as e:
                print(f"[Sheet] Error adding to Email Sheet: {e}")

    def update_email_status(self, email, stage_name, value):
        """
        Updates the status of a specific email stage.
        stage_name examples: "Primary Mail", "Follow Up 1" ... "Follow Up 5"
        """
        try:
            cell = self.email_worksheet.find(email) # Find row by email
            
            # Map stage name to column index (approximate or dynamic)
            # Headers: Email(1), Company(2), State(3), City(4), Niche(5), Pri(6), F1(7), F2(8), F3(9), F4(10), F5(11)
            col_map = {
                "Primary Mail": 6,
                "Follow Up 1": 7,
                "Follow Up 2": 8,
                "Follow Up 3": 9,
                "Follow Up 4": 10,
                "Follow Up 5": 11
            }
            
            col_idx = col_map.get(stage_name)
            if col_idx:
                self.email_worksheet.update_cell(cell.row, col_idx, value)
                print(f"[Sheet] Updated {email} {stage_name} -> {value}")
        except Exception as e:
            print(f"[Sheet] Failed to update status for {email}: {e}")

    def get_existing_domains(self):
        """Returns a set of websites already in the sheet to prevent dupes."""
        try:
            records = self.leads_worksheet.get_all_records()
            return set(r['Website'] for r in records if r.get('Website'))
        except:
            return set()

    def remove_invalid_leads(self, invalid_emails):
        """Removes leads with these emails from 'Leads with Email' sheet."""
        if not invalid_emails: return
        
        print(f"[Sheet] Removing {len(invalid_emails)} invalid emails...")
        
        # Strategy:
        # 1. Get all cells in Email column (Column 1)
        # 2. Find rows matching invalid emails
        # 3. Delete rows (from bottom up to preserve indices)
        
        try:
            # Column 1 is Email
            email_cells = self.email_worksheet.col_values(1)
            
            # Map Email -> Row Index (1-based)
            # Note: col_values returns list of strings. Index 0 is Row 1.
            
            rows_to_delete = []
            for idx, email_val in enumerate(email_cells):
                if email_val in invalid_emails:
                    rows_to_delete.append(idx + 1)
            
            # Sort descending
            rows_to_delete.sort(reverse=True)
            
            for row_idx in rows_to_delete:
                print(f"   Deleting row {row_idx} ({email_cells[row_idx-1]})")
                self.email_worksheet.delete_rows(row_idx)
                
            print(f"[Sheet] Successfully deleted {len(rows_to_delete)} rows.")
            
        except Exception as e:
            print(f"[Sheet] Error removing invalid leads: {e}")
