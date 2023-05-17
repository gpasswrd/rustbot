from __future__ import annotations
from config import *
import asyncio
from rustplus import RustSocket, CommandOptions, Command, FCMListener
import rustplus
import time as timing
import datetime
import json
import re
from player import Player
import arrow

with open("rustplus.py.config.json", "r") as input_file:
    fcm_details = json.load(input_file)
    
with open ("crafting_recipies.json", "r") as input_file:
    craftables = json.load(input_file)

class MyFCMListener(FCMListener):
    def __init__(self, fcm_details):
        super().__init__(fcm_details)
        self.counter = 1
        self.pairing = None
    
    def on_notification(self, obj, notification, data_message):
        global notif
        notif = (notification)
        if not self.pairing:
            self.pairing = asyncio.create_task(pairingNotification())



team_list = None
task = None
paired_switches = {}
prefix = "!"
options = CommandOptions(prefix=prefix)
rust_socket = RustSocket(pair_req["ip"], pair_req["port"], STEAMID, int(PLAYERTOKEN), command_options=options,)

async def load_saved_switches():
    try:
        with open("paired_switches.json", "r") as saved_switches:
            return json.load(saved_switches)
    except:
        pass
        
async def send_message(message):
    await rust_socket.send_team_message(str(message))

async def start_pairing(notif):
    global ent_id, pairing_time
    message = str(f"Pairing started for {notif['data']['title'] }. You have 45 seconds to type !pair1 (name) to add this switch.")
    await send_message(str(message))
    pairing_time = 1
    ent_id = int(json.loads(notif["data"]["body"])["entityId"])

async def format_seconds(seconds):
    duration = arrow.now().shift(seconds=seconds)
    if seconds < 3600:  # Check if duration is less than 1 hour
        formatted_duration = duration.format("m [minute]s and s [second]s")
    else:
        formatted_duration = duration.format("H [hour]s and m [minute]s")
    return formatted_duration

hourly_players = []
        
async def update_players():
    global hourly_players
    current_players = (await rust_socket.get_info()).players

    hourly_players.append(int(current_players))
    
    if len(hourly_players) > 60:
        hourly_players.pop(0)
        
    with open("playerhistory.json", "w+") as history:
        json.dump(hourly_players, history)

async def updateTeam():
    global team_list
    try:
        for team_member in (await rust_socket.get_team_info()).members:
            if not team_member.is_online:
                continue
            has_moved = await team_list[team_member.steam_id].updateLocation((team_member.x, team_member.y), timing.time())
            afk_status = team_list[team_member.steam_id].AFKstatus 
            
            if not afk_status and not has_moved:
                if (timing.time() - team_list[team_member.steam_id].AFKtime) >= AFKTimeout:
                    await send_message(f"Team member '{team_member.name}' has been AFK for {AFKTimeout//60} minutes")
                    team_list[team_member.steam_id].AFKstatus = True

            if afk_status and has_moved:
                await send_message(f"Team member '{team_member.name}' is no longer AFK after {round((timing.time()-team_list[team_member.steam_id].oldAFKTime)//60)} minutes")
                team_list[team_member.steam_id].AFKstatus = False
    except:
        team_list = {team_member.steam_id:Player( (team_member.x, team_member.y), team_member.steam_id, team_member.name, team_member.is_online) for team_member in (await rust_socket.get_team_info()).members}
        await updateTeam()

async def timer(seconds, switch_group):
    try:
        await asyncio.sleep(seconds-30)
        await send_message(f"Warning: Turning {switch_group} on automatically in 30 seconds.")
        await asyncio.sleep(30)
        await handleSwitch(switch_group, ["on"])
    except asyncio.CancelledError:
        print("Timer cancelled")

async def handleSwitch(command, args):
    switch_group = command
    switch_state = bool((await rust_socket.get_entity_info(paired_switches[switch_group][0])).value)
    if args:

        if args[0].lower() == "on":
            for switch_name in paired_switches[switch_group]:
                await rust_socket.turn_on_smart_switch(switch_name)
            await send_message(f"Turned {switch_group}: On")

        elif args[0].lower() == "off":
            for switch_name in paired_switches[switch_group]:
                await rust_socket.turn_off_smart_switch(switch_name)
            await send_message(f"Turned {switch_group}: Off")
        
        elif args[0].lower() == "status":
            await send_message(f"Showing status of switches paired as {switch_group}:")
            for switch_name in paired_switches[switch_group]:
                await asyncio.sleep(0.25)
                await send_message(f"Switch ID: {switch_name} is currently: {'On' if bool((await rust_socket.get_entity_info(switch_name)).value) else 'Off'}")
            
        elif args[0].lower() == "remove" or args[0].lower() == "delete":
            paired_switches.pop(switch_group)
            with open("paired_switches.json", "w") as saved_switches:
                json.dump(paired_switches, saved_switches)
            await send_message(f"{switch_group} was removed.")

        else:
            if len(args) == 2 and args[0] == "delay":
                global task
                if task:
                    task.cancel()
                try:
                    delay_time = int(args[1])
                    for switch_name in paired_switches[switch_group]:
                        await rust_socket.turn_off_smart_switch(switch_name)
                    await send_message(f"Turned {switch_group}: Off. Turning On automatically in {delay_time} minutes.")
                    task = asyncio.create_task(timer(delay_time*60, switch_group))

                except Exception as e:
                    print(e)
                    await send_message("Usage: !(switch name) (delay time)")

    else:
        if switch_state:
            for switch_name in paired_switches[switch_group]:
                await rust_socket.turn_off_smart_switch(switch_name)
            await send_message(f"Turned {switch_group}: Off")
        else:
            for switch_name in paired_switches[switch_group]:
                await rust_socket.turn_on_smart_switch(switch_name)
            await send_message(f"Turned {switch_group}: On")

def reconnectToServer():
    global rust_socket
    print("Lost Connection")
    raise ConnectionError

async def hours_to_seconds(currenttime:str):
    hours, minutes = currenttime.split(':')
    return (int(hours) * 3600 + int(minutes) * 60)

async def codeTest():
    print("a")
    print((await rust_socket.get_info()).size)
    for x in [x for x in (await rust_socket.get_team_info()).members if x.is_alive]:
        grid = rustplus.convert_xy_to_grid((x.x, x.y), (await rust_socket.get_info()).size)
        print(grid)
        await asyncio.sleep(1)

async def pairingNotification(notification):
    pass

class EventTracker:

    def __init__(self):
        self.type_to_name = {
            1:"Player",
            2:"Explosion",
            3:"Vending Machine",
            4:"CH47",
            5:"Cargo Ship",
            6:"Crate",
            7:"GenericRadius",
            8:"Patrol Helicopter"
        }
        self.last_seen = {}
        self.active_events = None
        self.active_events:list[rustplus.RustMarker]


    async def updateEvents(self):
        self.active_events = []
        for event in (await rust_socket.get_current_events()):
            if event.type in [4, 5, 8]:
                self.last_seen[event.type] = timing.time()
                active_events.append(event)

        if self.active_events:
            return True
        
    async def sendEvents(self):
        for event in self.active_events:
            await send_message(f"{self.type_to_name[event.type]} has entered the map @{rustplus.convert_xy_to_grid(event.x, event.y)}.")

    async def lastSeen(self, event_type):
        if event_type in self.last_seen.keys():
            await send_message(f"{self.type_to_name[event_type]} was last seen {await format_seconds(timing.time-self.last_seen[event_type])} ago.")
        else:
            await send_message(f"{self.type_to_name[event_type]} has not yet been seen.")
        
class RustBot:
    def __init__(self):
        pass

async def main():
    global rust_socket, notif, paired_switches, ent_id, pairing_time, craftables, team_list

    fcm_listener = MyFCMListener(fcm_details)
    fcm_listener.start()
    await rust_socket.connect(retries=10000)
    timing.sleep(1)
    event_tracker = EventTracker()
    team_list = {team_member.steam_id:Player( (team_member.x, team_member.y), team_member.steam_id, team_member.name, team_member.is_online) for team_member in (await rust_socket.get_team_info()).members}

    notif = None
    ignore_notif = False

    update_timer = 119
    pairing_time = 0

    paired_switches = (await load_saved_switches())

    print("Connected.")
    last_message = None
    while True:

        await asyncio.sleep(1)


        if update_timer >= 120:
            #await update_players()
            update_timer = 0
        update_timer += 1

        if update_timer % 3 == 0:
            await updateTeam()
            if (await event_tracker.updateEvents()):
                (await event_tracker.sendEvents())

        if notif and ignore_notif == False:
            print("a")
            if notif["data"]["channelId"] == "pairing":
                print("if")
                await start_pairing(notif)
            else:
                print(notif["data"]["channelId"])
                print("else")
            notif = None
        
        message = (await rust_socket.get_team_chat())[-1].message
        if message == last_message:
            continue
        last_message = message

        print(message)
        
        if message[0] == prefix and len(message) > 1:
            command = message[1:].split()[0]
            try:
                args = message[1:].split()[1:]
            except:
                args = None
            
            if command in paired_switches.keys():
                await handleSwitch(command, args)
                
        if pairing_time > 0:
            pairing_time += 1
        if pairing_time > 90:
            pairing_time = 0

@rust_socket.command
async def afk(command:Command):
    sentAFK = False
    for steam_id, member in team_list.items():
        if member.AFKstatus == True:
            await send_message(f"Team member '{member.name}' has been AFK for {round((timing.time()-member.AFKtime)//60)} minutes")
            sentAFK = True
    if not sentAFK:
        await send_message(f"No team members are currently AFK.")

@rust_socket.command
async def time(command:Command):

    time_info = (await rust_socket.get_time())

    currenttime = await hours_to_seconds(time_info.time)

    sunset = await hours_to_seconds(time_info.sunset)
    sunrise = await hours_to_seconds(time_info.sunrise)
    if currenttime > sunset or currenttime < sunrise:

        if currenttime > sunset:
            delta_time = (((currenttime-sunset+sunrise)/(3600/305))/90)
        elif currenttime < sunrise:
            print("before sunrise")
            delta_time = (((sunrise-currenttime)/(3600/305))/90)
        # Night
        await send_message(f"The current Rust time is {time_info.time}. {round(delta_time)} minutes until sunrise.")

    if currenttime < sunset and currenttime > sunrise:
    # if time is before sunset and time is after sunrise
        delta_time = (((sunset-currenttime)/(3600/305))/90)
        # Day
        await send_message(f"The current Rust time is {time_info.time}. {round(delta_time)} minutes until sunset.")

@rust_socket.command
async def events1(command:Command):
    
    event_types = {8:"Patrol Helicopter", 6:"Locked Crate", 5:"Cargo", 4:"CH47", 2:"Explosion"}
    
    events = await rust_socket.get_current_events()
    for event in events:
        await send_message(f"{event_types[event.type]} @ Coordinates X: {event.x}, Y: {event.y}")
        print()

@rust_socket.command
async def pair1(command:Command):
    global pairing_time
    print("paired")
    if pairing_time:
        args = command.args
        if len(args) != 1:
            await send_message(f"Usage: !pair (label)")
            return
        
        await send_message(f"Paired switch as \"{args[0]}\". You can now turn this switch on/off by using \"!{args[0]}\"")
        #paired_switches[args[0]] = ent_id
        try:
            paired_switches[args[0]].append(ent_id)
        except:
            paired_switches[args[0]] = [ent_id]
        pairing_time = 0
        print(paired_switches)
        with open("paired_switches.json", "w") as saved_switches:
            json.dump(paired_switches, saved_switches)
            
@rust_socket.command
async def pop(command:Command):
        
    server_info = await rust_socket.get_info()
    current_players = server_info.players

    message = f"Current players: {current_players} / {server_info.max_players}. "
    
    if server_info.queued_players > 0:
        message += f"{server_info.queued_players} in queue. "

    await send_message(str(message))

@rust_socket.command
async def craftcost(command:Command):
    args = command.args
    print(args)

    if not args:
        await send_message(f"Correct usage: \"{prefix}craftcost (item) (amount)\"")
        return
    
    if args[0].lower() == "help":
        print("craftcost help")
    
    if args[0].lower() == "add":
        if len(args) >= 3:
            try:
                
                pattern = r'(\w[\w\s]*):(\d+)'
                matches = re.findall(pattern, args[2])

                craftables[args[1]] = {key.strip(): int(value) for key, value in matches}
                await send_message(str(craftables))
                
                with open("crafting_recipies.json", "w+") as saved_recipies:
                    json.dump(craftables, saved_recipies)
                saved_recipies.close()
                return
                
            except Exception as e:
                await send_message(str(e))
                #await send_message(f"Correct usage: \"{prefix}craftcost add (item name) ({{ingredient1:amount, ingredient2:amount, etc..}})")
                return 
    
    if args[0].lower() in craftables.keys():
        if len(args) > 1:
            if args[1].isdigit():
                
                num = int(args[1])
                
                await send_message(f"Calculating crafting cost for {num} {args[0].lower()}...")
                message = ""
                costs = craftables[args[0].lower()]
                for item in costs.keys():
                    temp = costs[item]*num
                    message += f"{item}: {temp}, "
                    
                await send_message(f"Craft cost for {num} {args[0].lower()}: {message[:len(message)-2]}.")
                return
    else:
        await send_message(f"Unknown item. Available items: {', '.join([str(x) for x in craftables.keys()])}")
        return
 

@rust_socket.command
async def alivetime(command:Command):
    args = command.args
    print("a")
    team = (await rust_socket.get_team_info())
    if args:
        for member in team.members:
            if args[0].lower() in member.name.lower():
                await send_message(f"Team member: {member.name} has been alive for { datetime.timedelta(seconds = round(timing.time()-member.spawn_time)) } hours.")

@rust_socket.command
async def promote(command:Command):
    args = command.args
    print("a")
    for member in (await rust_socket.get_team_info()).members:
    
        if member.name == " ".join(args):
            print("b")
            await rust_socket.promote_to_team_leader(member.steam_id)
            await send_message(f"Sucessfully promoted {member.name} to leader.")

loop = asyncio.get_event_loop()
while True:
    try:
        asyncio.run(main())

    except Exception as e:
        print(e)
        timing.sleep(20)
        continue