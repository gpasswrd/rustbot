import rustplus
import asyncio
import time
from utils import *

class Event:
    def __init__(self, type:int):
        self.type = type
        self.previous_active = False
        self.active = False
        self.last_seen = None
        self.marker = None
        self.marker:rustplus.RustMarker

class EventTracker:
    def __init__(self, rust_socket):
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

        self.monitored_events = [4, 5, 8]

        self.event_dict = {type:Event(type) for type in self.type_to_name.keys()}
        self.rust_socket = rust_socket
        self.rust_socket:rustplus.RustSocket


    async def updateEvents(self):
        current_events = (await self.rust_socket.get_current_events())
        map_size = (await self.rust_socket.get_info()).size

        for event in self.event_dict.values():
            event.previous_active = event.active
            event.active = False

        for marker in current_events:
            if marker.type in self.monitored_events:
                self.event_dict[marker.type].active = True
                self.event_dict[marker.type].last_seen = time.time()
                self.event_dict[marker.type].marker = marker
        
        for event in self.event_dict.values():
            if event.active == event.previous_active:
                continue

            if event.active == True:
                await self.rust_socket.send_team_message(f"{self.type_to_name[event.type]} has entered the map @{''.join(rustplus.convert_xy_to_grid((event.marker.x, event.marker.y), map_size, False))}.")
                print(f"{self.type_to_name[event.type]} has entered the map @{''.join(rustplus.convert_xy_to_grid((event.marker.x, event.marker.y), map_size, False))}.")

            elif event.active == False and event.type != 8:
                await self.rust_socket.send_team_message(f"{self.type_to_name[event.type]} has left the map.")
                print(f"{self.type_to_name[event.type]} has left the map.")

            else:
                if event.type == 8:
                    await self.rust_socket.send_team_message(f"Patrol Helicoper was taken down @{''.join(rustplus.convert_xy_to_grid((event.marker.x, event.marker.y), map_size, False))}")  
                    print(f"Patrol Helicoper was taken down @{''.join(rustplus.convert_xy_to_grid((event.marker.x, event.marker.y), map_size, False))}")                        
    

    async def lastSeen(self, event_type):
        if event_type in self.event_dict.keys() and self.event_dict[event_type].last_seen:
            await self.rust_socket.send_team_message(f"{self.type_to_name[event_type]} was last seen {await format_seconds(time.time-self.event_dict[event_type].last_seen)} ago.")
            print(f"{self.type_to_name[event_type]} was last seen {await format_seconds(time.time-self.event_dict[event_type].last_seen)} ago.")
        else:
            await self.rust_socket.send_team_message(f"{self.type_to_name[event_type]} has not yet been seen.")
            print(f"{self.type_to_name[event_type]} has not yet been seen.")