version=$(curl -s "http://localhost:4444/wd/hub/status")
size=${#version}
if (($size < 10)); then
  echo "starting selenium server in background"
  nohup xvfb-run java -Dwebdriver.chrome.driver=/usr/bin/chromedriver -jar /usr/bin/selenium/selenium-server-standalone.jar &
  echo "selenium server started, waiting for bootup"
  sleep 10s
  echo "wait finished"
fi
cd /home/arthur/python/judicial

if [[ -z $1 ]]; then 
  years="ALL"
else
  years=$1
fi

if [[ -z $2 ]]; then 
  districts="ALL"
else
  districts=$2
fi

if [[ -z $3 ]]; then 
  instances="ALL"
else
  instances=$3
fi

if [[ -z $4 ]]; then 
  specialized="ALL"
else
  specialized=$4
fi

echo $years
echo $districts
echo $instances
echo $specialized
python3.9 -u main.py "${years}" "${districts}" "${instances}" "${specialized}" --sql_saver -m INFO > task_logs.txt
