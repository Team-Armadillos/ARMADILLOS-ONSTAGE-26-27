import unittest
from core.state_manager import StateManager
from core.trigger_manager import TriggerManager
from core.event_manager import EventManager,Event
from core.scene_manager import SceneManager
class CoreTests(unittest.TestCase):
    def test_trigger_conditions(self):
        state=StateManager();state.set('scene','fairy_off');state.set('godparents_off',True)
        actions=[];manager=TriggerManager(state,actions.append)
        manager.add({'event':'wand_detected','when':{'scene':'fairy_off','godparents_off':True},'actions':[{'type':'scene','name':'fairy_saved'}]})
        manager.handle(Event('wand_detected'))
        self.assertEqual(actions[0]['name'],'fairy_saved')
    def test_priority(self):
        bus=EventManager();seen=[];bus.subscribe(lambda event:seen.append(event.name))
        bus.emit('low',priority=0);bus.emit('high',priority=10);bus.drain()
        self.assertEqual(seen,['high','low'])
    def test_scene(self):
        state=StateManager();seen=[];scene=SceneManager(state,seen.append)
        scene.configure({'one':{'image':'test'}});scene.go('one');scene.restart()
        self.assertEqual(len(seen),2)
if __name__=='__main__':unittest.main()
