<div align="right">
  <a href="README.md">
    <img src="https://img.shields.io/badge/Language-T%C3%BCrk%C3%A7e-blue?style=for-the-badge" alt="Türkçe Oku">
  </a>
</div>

![LibreOffice Calc Çoklu Belge Arama Ekran Görüntüsü](https://raw.githubusercontent.com/erdincyz/gorseller/refs/heads/main/_cesitli/libre_calc_coklu_ara_ekran_goruntusu.jpg)


# LibreOffice Calc Multi-Document Search Macro

This project is a Python-based macro that allows you to search across all open LibreOffice Calc (spreadsheet) documents simultaneously.

Unlike the standard LibreOffice search function, it scans all tabs and files in a single interface, lists the results, and does not freeze the system.

## Features

* **Multi-Scan:** Search only the active sheet or across all open LibreOffice documents.
* **Advanced Search Options:**
  * **Fuzzy Search:** Finds the closest matches even if you misspell a word.
  * **Regex:** Complex pattern matching using regular expressions.
  * **Whole Word & Case Sensitivity.**
* **Quick Access:** Double-clicking a result in the list instantly takes you to the corresponding cell in that document.
* **Export:** Save the found results in `.csv` format with a single click.
* **High Performance & Safety:** The search process runs in the background (Worker Thread). LibreOffice won't freeze or crash, even with files containing hundreds of thousands of rows. Memory protection is included to prevent excessive RAM consumption.

---

## Installation

LibreOffice looks for Python macros in specific folders depending on your operating system. To install, simply download the `coklu_belgede_ara.py` file and copy it to the appropriate folder for your OS.

**Important:** If the `Scripts` and `python` folders do not exist in the specified paths, you must create them yourself (pay attention to case sensitivity).

### 🪟 Windows Installation
1. Download the `coklu_belgede_ara.py` file.
2. Press `Windows + R` on your keyboard to open the "Run" dialog.
3. Copy and paste the following path and press Enter:
   `%APPDATA%\LibreOffice\4\user\Scripts\`
4. If a folder named `python` doesn't exist there, create it.
5. Copy the downloaded `.py` file into this `python` folder.
   *(The full path should look like this: `C:\Users\YourUsername\AppData\Roaming\LibreOffice\4\user\Scripts\python\coklu_belgede_ara.py`)*

### 🐧 Linux Installation
On Linux distributions, the `tkinter` package must be installed on your system for the UI window to work.
1. Open the terminal and install tkinter:
   * Debian/Ubuntu-based systems: `sudo apt-get install python3-tk`
   * Fedora/RHEL-based systems: `sudo dnf install python3-tkinter`
2. Open your file manager and enable the `Show Hidden Files` option (usually `Ctrl + H`).
3. Navigate to: `~/.config/libreoffice/4/user/Scripts/python/`
   *(If the folders don't exist, you can create them via terminal: `mkdir -p ~/.config/libreoffice/4/user/Scripts/python`)*
4. Copy the downloaded `.py` file into this folder.

### 🍎 macOS Installation
1. Download the `coklu_belgede_ara.py` file.
2. Open Finder, click on the **Go** option in the top menu.
3. Hold down the `Option (Alt)` key on your keyboard. The **Library** option will appear in the menu; click on it.
4. Navigate to: `Application Support/LibreOffice/4/user/Scripts/python/`
   *(If the `Scripts` and `python` folders don't exist, create them).*
5. Drop the downloaded file here.

---

## ⚙️ Adding a Button to the Menu

After placing the file, let's add a button so LibreOffice recognizes it and you can run it easily.

1. Completely close and reopen **LibreOffice Calc**.
2. Go to **Tools > Customize** from the top menu.
3. Go to the **Menus** tab.
4. Look at the Search box or the Category section:
   * Navigate to **LibreOffice Macros** > **My Macros** > **coklu_belgede_ara**.
   * You will see `CokluAramaMacro` there.
5. Add it to the menu using the right arrow (`->`).
6. If you want, right-click the added item and rename it to **"Multi Search"** (or anything you prefer).

You can now run it by clicking the button in the menu!

---

## Technical Notes

* The macro stores your settings and recent search history on your computer in the `~/.multi_search_config.json` file.
* To prevent UI crashes, potential errors are logged to the `~/.multi_search.log` file. You can review this file if you experience any issues.
