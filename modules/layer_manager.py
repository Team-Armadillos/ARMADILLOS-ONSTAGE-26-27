"""Independent visual layers with alpha, z-order and bounds."""
from dataclasses import dataclass
from PIL import Image
@dataclass
class Layer:
    image: object
    x: float=0
    y: float=0
    width: float=1
    height: float=1
    z: int=0
    opacity: float=1
    visible: bool=True

class LayerManager:
    def __init__(self): self.layers={}
    def set(self,name,image,**kwargs): self.layers[name]=Layer(image,**kwargs)
    def remove(self,name): self.layers.pop(name,None)
    def clear(self): self.layers.clear()
    def compose(self,width,height,background=(0,0,0,255)):
        result=Image.new("RGBA",(width,height),background)
        for layer in sorted(self.layers.values(),key=lambda layer:layer.z):
            if not layer.visible or layer.image is None: continue
            x,y=int(layer.x*width),int(layer.y*height)
            w,h=max(1,int(layer.width*width)),max(1,int(layer.height*height))
            img=layer.image.resize((w,h),Image.Resampling.LANCZOS).convert("RGBA")
            if layer.opacity<1:
                alpha=img.getchannel("A").point(lambda v:int(v*max(0,min(1,layer.opacity))))
                img.putalpha(alpha)
            result.alpha_composite(img,(x,y))
        return result
