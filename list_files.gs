function listDriveFiles() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  sheet.clearContents();

  sheet.appendRow(["Name", "Size (bytes)", "Extension", "Modified"]);
  sheet.getRange(1, 1, 1, 4).setFontWeight("bold");

  var emailFolders = DriveApp.getFoldersByName("email");
  if (!emailFolders.hasNext()) {
    sheet.appendRow(["ERROR: 'email' folder not found"]);
    return;
  }
  var emailFolder = emailFolders.next();

  var allFolders = emailFolder.getFoldersByName("all");
  if (!allFolders.hasNext()) {
    sheet.appendRow(["ERROR: 'all' folder not found inside 'email'"]);
    return;
  }
  var allFolder = allFolders.next();

  var files = allFolder.getFiles();
  var row = 2;
  while (files.hasNext()) {
    var file = files.next();
    var name = file.getName();
    var size = file.getSize();
    var ext = name.includes(".") ? name.split(".").pop() : "(none)";
    var modified = file.getLastUpdated();
    sheet.getRange(row, 1, 1, 4).setValues([[name, size, ext, modified]]);
    row++;
  }

  SpreadsheetApp.getUi().alert("Done! " + (row - 2) + " files listed.");
}
