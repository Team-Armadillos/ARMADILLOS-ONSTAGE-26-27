"""Declarative triggers with event and state conditions."""
class TriggerManager:
    def __init__(self,state,action): self.state=state;self.action=action;self.rules=[]
    def add(self,rule): self.rules.append(rule)
    def handle(self,event):
        for rule in self.rules:
            if rule.get("event")!=event.name: continue
            if not self.state.matches(rule.get("when",{})): continue
            if any(event.data.get(k)!=v for k,v in rule.get("data",{}).items()): continue
            for action in rule.get("actions",[]): self.action(action)
