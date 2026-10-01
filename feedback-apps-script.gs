// Receives dashboard feedback and appends one row per submission to a Google Sheet.
//
// Setup (about 3 minutes, signed in as aldarsignatureproject@gmail.com):
// 1. Create a Google Sheet, e.g. "Macro Signals feedback".
// 2. Extensions > Apps Script. Replace the editor contents with this file. Save.
// 3. Deploy > New deployment > type "Web app".
//    Execute as: Me. Who has access: Anyone. Deploy, and approve the permission prompt.
// 4. Copy the web app URL (ends in /exec) and paste it into FEEDBACK_URL in index.html.
//
// Note: the URL is public, so anyone who finds it could post rows. Fine for a prototype.

const HEADERS = ['received', 'digest', 'role', 'kind', 'item', 'title', 'vote', 'reasons', 'comment', 'tenor', 'link'];

function doPost(e) {
  const d = JSON.parse(e.postData.contents);
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  if (sheet.getLastRow() === 0) sheet.appendRow(HEADERS);
  sheet.appendRow([
    new Date(), d.digest || '', d.role || '', d.kind || '', d.item || '', d.title || '',
    d.vote || '', (d.reasons || []).join('; '), d.comment || '', d.tenor || '', d.link || '',
  ]);
  return ContentService.createTextOutput('ok');
}
