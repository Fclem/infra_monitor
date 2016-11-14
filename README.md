# infra_monitor
a generic services monitoring system that can update a remote status page service like StatusPage.io or StatusCake.com
Supports 'update' scheme (on local check status change), or 'PUSH' scheme (send a GET request at regular interval if local check status is ON, i.e. heartbeat)
This is a generic module, meant to be implemented for other status page services.

## How to start :
```bash
my_implementation_folder="my_implentation"
mkdir $my_implementation_folder && cd $my_implementation_folder
git clone https://github.com/Fclem/infra_monitor.git
```
Then add `from infra_monitor import *` at the top of your code.
Existing implementations :
 * for [StatusPage](https://www.statuspage.io/) [StatusPage.io_monitor](https://github.com/Fclem/StatusPage.io_monitor)
 * for [StatusCake](https://www.statuscake.com/) [StatusCake_monitor](https://github.com/Fclem/StatusCake_monitor)  

Checks are loaded from `config.ini`, which contains all parameters, like urls, keys, refresh_interval, etc

## Currently supported checks types :
 * `url` : if HTTP GET to *url* returns HTTP 200
 * `tcp` : if connection to TCP *host port* is successful
 * `ping` : if remote *host* replies to ICMP ping (through system's ping command)

## To be supported checks types :
 * `docker` : if a named docker container is running
