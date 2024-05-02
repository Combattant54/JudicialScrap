<h1>How to use this script</h1>
<h2>1) Using a linux server</h2>
<h3>Installation</h3>
Install a chromium driver for linux on path "/usr/bin/chromedriver"
Run "pip install -r requirements.txt" in the folder with all the scripts
<h3>Run the script</h3>
Start the file "start.sh" in root mode using arguments : 
  - the years : a single year, a list of years separeted by ';' or a years range separeted by '-' <br>
  - the districts : the districts in full maj separeted by ';' or 'ALL' for every district <br>
  - the instances : the instances in full maj separeted by ';' or 'ALL' for every instance <br>
  - the specialized : the specialized in full maj separeted by ';' or 'ALL' for every specialized <br>

The command should look like this : "start.sh 2018-2024 ALL 'SALA SUPERIOR;JUZGADO MIXTO;JUZGADO ESPECIALIZADO' 'FAMILIA CIVIL' &" <br>
You should put the final "&" on the command !!

Then, press enter and run disown to put the script in background<br>

You can access the current data using the given command ( 'curl http://127.0.0.1:<port>' )
