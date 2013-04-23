# -*- coding: utf-8 -*-
from __future__ import absolute_import

from sc2reader.data import Unit
from sc2reader.events.base import Event
from sc2reader.log_utils import loggable

@loggable
class GameEvent(Event):
    name = 'GameEvent'

    """Abstract Event Type, should not be directly instanciated"""
    def __init__(self, frame, pid, event_type):
        super(GameEvent, self).__init__(frame, pid)

        self.type = event_type
        self.is_local = (pid != 16)
        event_class = event_type >> 4
        self.is_init = (event_class == 0)
        self.is_player_action = (event_class == 1)
        self.is_camera_movement = (event_class == 3)


class UnknownEvent(GameEvent):
    name = 'UnknownEvent'

class BetaJoinEvent(GameEvent):
    name = 'BetaJoinEvent'

    def __init__(self, frames, pid, event_type, flags):
        super(BetaJoinEvent, self).__init__(frames, pid, event_type)
        self.flags = flags

# TODO: András says this is just a leave event and not a win event!
# Investigate
class BetaWinEvent(GameEvent):
    name = 'BetaWinEvent'

    def __init__(self, frames, pid, event_type, flags):
        super(BetaWinEvent, self).__init__(frames, pid, event_type)
        self.flags = flags

class PlayerJoinEvent(GameEvent):
    name = 'PlayerJoinEvent'

    def __init__(self, frames, pid, event_type, flags):
        super(PlayerJoinEvent, self).__init__(frames, pid, event_type)
        self.flags = flags

class GameStartEvent(GameEvent):
    name = 'GameStartEvent'

class PlayerLeaveEvent(GameEvent):
    name = 'PlayerLeaveEvent'

class CameraEvent(GameEvent):
    name = 'CameraEvent'

    def __init__(self, frames, pid, event_type, x, y, distance, pitch, yaw, height_offset):
        super(CameraEvent, self).__init__(frames, pid, event_type)
        self.x, self.y = x, y
        self.distance = distance
        self.pitch = pitch
        self.yaw = yaw
        self.height_offset = height_offset

    def __str__(self):
        return self._str_prefix() + "{0} at ({1}, {2})".format(self.name, self.x,self.y)

class PlayerActionEvent(GameEvent):
    name = 'PlayerActionEvent'

@loggable
class SendResourceEvent(PlayerActionEvent):
    name = 'SendResourceEvent'

    def __init__(self, frames, pid, event_type, target, minerals, vespene, terrazine, custom):
        super(SendResourceEvent, self).__init__(frames, pid, event_type)
        self.sender = pid
        self.reciever = target
        self.minerals = minerals
        self.vespene = vespene
        self.terrazine = terrazine
        self.custom = custom

    def __str__(self):
        return self._str_prefix() + " transfer {0} minerals, {1} gas, {2} terrazine, and {3} custom to {4}" % (self.minerals, self.vespene, self.terrazine, self.custom, self.reciever)

    def load_context(self, replay):
        super(SendResourceEvent, self).load_context(replay)
        # DJ disabled this on 20130222 because GGTracker doesnt use this event
        # and it is currently broken for a replay thats now in the test suite.
        #
        # self.sender = replay.player[self.sender]
        # self.reciever = replay.players[self.reciever]

@loggable
class RequestResourceEvent(PlayerActionEvent):
    name = 'RequestResourceEvent'

    def __init__(self, frames, pid, event_type, minerals, vespene, terrazine, custom):
        super(RequestResourceEvent, self).__init__(frames, pid, event_type)
        self.minerals = minerals
        self.vespene = vespene
        self.terrazine = terrazine
        self.custom = custom

    def __str__(self):
        return self._str_prefix() + " requests {0} minerals, {1} gas, {2} terrazine, and {3} custom" % (self.minerals, self.vespene, self.terrazine, self.custom)

@loggable
class AbilityEvent(PlayerActionEvent):
    name = 'AbilityEvent'

    def __init__(self, frame, pid, event_type, ability, flags):
        super(AbilityEvent, self).__init__(frame, pid, event_type)
        self.ability_code = ability
        self.ability_name = 'Uknown'
        self.flags = flags

    def load_context(self, replay):
        super(AbilityEvent, self).load_context(replay)
        if not replay.datapack:
            return

        if self.ability_code not in replay.datapack.abilities:
            if not getattr(replay, 'marked_error', None):
                replay.marked_error=True
                self.logger.error(replay.filename)
                self.logger.error("Release String: "+replay.release_string)
                for player in replay.players:
                    self.logger.error("\t"+str(player))

            self.logger.error("{0}\t{1}\tMissing ability {2} from {3}".format(self.frame, self.player.name, hex(self.ability_code) if self.ability_code!=None else None, replay.datapack.__class__.__name__))

        else:
            self.ability = replay.datapack.abilities[self.ability_code]
            self.ability_name = self.ability.name


    def __str__(self):
        return self._str_prefix() + "Ability (%s) - %s" % (hex(self.ability_code), self.ability_name)

@loggable
class TargetAbilityEvent(AbilityEvent):
    name = 'TargetAbilityEvent'

    def __init__(self, frame, pid, event_type, ability, flags, target, player, team, location):
        super(TargetAbilityEvent, self).__init__(frame, pid, event_type, ability, flags)
        self.target = None
        self.target_id, self.target_type = target

        self.target_owner = None
        self.target_owner_id = player
        self.target_team = None
        self.target_team_id = team
        self.location = location

    def load_context(self, replay):
        super(TargetAbilityEvent, self).load_context(replay)

        """ Disabled since this seems to have gone out of bounds
            sc2reader/ggtracker/204927.SC2Replay
        if self.target_owner_id:
            print replay.people
            print self.target_owner_id
            self.target_owner = replay.player[self.target_owner_id]
        """

        """ Disabled since team seems to always be the same player
        if self.target_team_id:
            self.target_team = replay.team[self.target_team_id]
        """

        if not replay.datapack:
            return

        if self.target_id in replay.objects:
            self.target = replay.objects[self.target_id]
            if not self.target.is_type(self.target_type):
                replay.datapack.change_type(self.target, self.target_type, self.frame)

        else:
            if self.target_type not in replay.datapack.units:
                self.logger.error("{0}\t{1}\tMissing unit {2} from {3}".format(self.frame, self.player.name, hex(self.target_type), replay.datapack.id))
                unit = Unit(self.target_id, 0x00)

            else:
                unit = replay.datapack.create_unit(self.target_id, self.target_type, 0x00, self.frame)

            self.target = unit
            replay.objects[self.target_id] = unit

    def __str__(self):
        if self.target:
            if isinstance(self.target, Unit):
                target = "{0} [{1:0>8X}]".format(self.target.name, self.target.id)
            else:
                target = "{0:X} [{1:0>8X}]".format(self.target[1], self.target[0])
        else:
            target = "NONE"

        return AbilityEvent.__str__(self) + "; Target: {0}".format(target)

@loggable
class LocationAbilityEvent(AbilityEvent):
    name = 'LocationAbilityEvent'

    def __init__(self, frame, pid, event_type, ability, flags, location):
        super(LocationAbilityEvent, self).__init__(frame, pid, event_type, ability, flags)
        self.location = location

    def __str__(self):
        return AbilityEvent.__str__(self) + "; Location: %s" % str(self.location)

@loggable
class SelfAbilityEvent(AbilityEvent):
    name = 'SelfAbilityEvent'

    def __init__(self, frame, pid, event_type, ability, flags, info):
        super(SelfAbilityEvent, self).__init__(frame, pid, event_type, ability, flags)
        self.info = info

@loggable
class HotkeyEvent(PlayerActionEvent):
    name = 'HotkeyEvent'

    def __init__(self, frame, pid, event_type, hotkey, deselect):
        super(HotkeyEvent, self).__init__(frame, pid, event_type)
        self.hotkey = hotkey
        self.deselect = deselect

class SetToHotkeyEvent(HotkeyEvent):
    name = 'SetToHotkeyEvent'

class AddToHotkeyEvent(HotkeyEvent):
    name = 'AddToHotkeyEvent'

class GetFromHotkeyEvent(HotkeyEvent):
    name = 'GetFromHotkeyEvent'

@loggable
class SelectionEvent(PlayerActionEvent):
    name = 'SelectionEvent'

    def __init__(self, frame, pid, event_type, bank, objects, deselect):
        super(SelectionEvent, self).__init__(frame, pid, event_type)
        self.bank = bank
        self.raw_objects = objects
        self.deselect = deselect

    def load_context(self, replay):
        super(SelectionEvent, self).load_context(replay)

        if not replay.datapack:
            return

        units = list()
        for (unit_id, unit_type, unit_flags) in self.raw_objects:
            # Hack that defaults viking selection to fighter mode instead of assault
            if replay.versions[1] == 2 and replay.build >= 23925 and unit_type == 71:
                unit_type = 72

            if unit_id in replay.objects:
                unit = replay.objects[unit_id]
                if not unit.is_type(unit_type):
                    replay.datapack.change_type(unit, unit_type, self.frame)
            else:
                if unit_type in replay.datapack.units:
                    unit = replay.datapack.create_unit(unit_id, unit_type, unit_flags, self.frame)
                else:
                    msg = "Unit Type {0} not found in {1}"
                    self.logger.error(msg.format(hex(unit_type), replay.datapack.__class__.__name__))
                    unit = Unit(unit_id, unit_flags)

                replay.objects[unit_id] = unit

            units.append(unit)

        self.units = self.objects = units

    def __str__(self):
        return GameEvent.__str__(self)+str([str(u) for u in self.objects])