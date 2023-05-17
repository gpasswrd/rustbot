class Player:
    def __init__(self, coords:tuple, steamid:int, name:str, online:bool):
        self.AFKtime = 0
        self.coords = (coords, self.AFKtime)
        self.steamid = steamid
        self.name = name
        self.online = online
        self.AFKstatus = False
        self.oldAFKTime = 0
        self.oldOnline = online
        self.onlineTime = 0

    async def updateLocation(self, new_coords, time) -> bool:

        if self.coords == new_coords:
            return False
        else:
            self.coords = new_coords
            self.oldAFKTime = self.AFKtime
            self.AFKtime= time
            return True
        
    async def updateOnline(self, new_status, time) -> bool:
        if self.online == new_status:
            return (False, 0)
        else:
            self.online = new_status
            self.onlineTime = time
            return (True, time)
