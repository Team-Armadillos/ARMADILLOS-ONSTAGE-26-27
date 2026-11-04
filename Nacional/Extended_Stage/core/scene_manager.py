"""Scene transitions and restarts."""
class SceneManager:
    def __init__(self,state,apply): self.state=state;self.apply=apply;self.scenes={}
    def configure(self,scenes): self.scenes=scenes
    def go(self,name):
        if name not in self.scenes: raise ValueError(f"Unknown scene: {name}")
        self.state.set("scene",name)
        self.apply(self.scenes[name])
    def restart(self):
        name=self.state.get("scene")
        if name: self.go(name)
