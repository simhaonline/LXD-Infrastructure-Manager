from flask import Flask
from flask import render_template
from flask import jsonify
from flask import session
from flask import request
from flask import Response
from flask import make_response
from application.socket import lxd_socketio
from application.api import LxdApi
from application.api import SshApi
from application.api.servers import Servers
#from flask_socketio import SocketIO
from config import Config
import time
import random
import pdb
import json


app = Flask(__name__)
app.debug = True #TODO REMOVE FOR LIVE
app.config["SECRET_KEY"] = "secret!" #TODO ACTUAL SECRET KEY
socketio = lxd_socketio()
lxd_api = LxdApi()
global config
thread = None
servers = None

@app.route("/")
def main():
#     containers = {}
#     for s in config:
#         containers[s] = lxd_api.get_container_info(s)
# 
#     #ssh = SshApi(config)
#     #server_info = {}
#     #for s in config:
#     #    server_info[s] = ssh.get_server_info(s)
# 
#     print '[[['
#     print config
#     print containers
#     print ']]]'
#     vals = {
# #        "servers": config,
# #        "containers": containers,
# #        "server_info": server_info,
#     }
#    return render_template("index.html", **vals)
    return render_template("index.html")

@app.route("/get_info/")
def get_info_r():
    containers = {}
    for s in config:
        containers[s] = lxd_api.get_container_info(s)

    vals = {
        "servers": servers.get_display_info(),
        "containers": containers,
#        "server_info": server_info,
    }
    
    return jsonify(vals)

@app.route("/container_cmd/", methods=["POST"])
def container_cmd_handler():
    if request.method == "POST":
        req_data = request.get_json()
        server = req_data.get("server")
        container = req_data.get("container")
        method = req_data.get("method")
        snap = req_data.get("snap")
        tar_name = '' or req_data.get("tar_name")
        if req_data.get("type") == "container":
            lxd_api.exec_container_cmd(server, container, method, tar_name)
            # get update container info after method
            c_info = get_container_info(server, container)
            return make_response(jsonify(c_info))
        elif req_data.get("type") == "snapshot":
            lxd_api.exec_snapshot_cmd(server, snap, container, method)
            c_info = get_container_info(server, container)
            return make_response(jsonify(c_info))

def get_container_info(server, container):
    field_translations = {
        "name": "name",

    }
    for c in lxd_api.get_container_info(server):
        if c["name"] == container:
            return c

def update_thread():
#    global servers
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        socketio.sleep(5)
        count += 1
        mes = {}
        if servers:
            for s in servers.get():
                mes.update({s : servers.get(s).get_info()})
            mes = json.dumps(mes)
            
            socketio.emit('my_response',
                           mes,
                          namespace='/update')
        
@socketio.on("connected", namespace="/update")
def got_event(msg):
    global thread
    if thread is None:
        thread = socketio.start_background_task(target=update_thread)
    socketio.emit('my_response', {'data': 'Connected', 'count': 0})

@app.after_request
def add_header(response):
    #TODO REMOVE FOR LIVE
    response.headers["Cache-Control"] = "public, max-age=0"
    return response

""" setup / run app """
def _get_configuration():
    f = file("server_cfg.cfg")
    cfg = Config(f)
    config = {}

    for server in cfg.servers:
        config[server.name] = {
            "servername": server.name,
            "username": server.username,
            "password": server.password,
            "endpoint": server.endpoint,
            "cert": (server.certfile,server.keyfile),
            "verify": server.verify,
            "keyfile": server.keyfile,
            "certfile": server.certfile,
            "rgba_color": "rgba(%s,%s,%s,1)" % (
                    random.randrange(255),
                    random.randrange(255),
                    random.randrange(255)
            ),
            "excluded_containers": tuple(server.excluded_containers),
        }
    return config

def config_app():
    print "1"
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    print "2"
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    print "3"
    global config
    config = _get_configuration()
    print "4"
    socketio.init_app(app)
    print "5"
    socketio.set_lxd_config(config)
    print "6"
    lxd_api.set_config(config)
# New
    global servers
    print "7"
    servers = Servers(config)
    print "8"
    #servers.execute_ssh_command()


if __name__ == "__main__":
    config_app()
    socketio.run(app, host='0.0.0.0')
