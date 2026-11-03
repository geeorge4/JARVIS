"""Short command endpoint detector, independent of microphone hardware."""
class EndOfSpeech:
    def __init__(self):
        self.blocks=0;self.heard=False;self.quiet=0;self.noise=.0015
    def feed(self,rms):
        self.blocks+=1
        threshold=max(.0025,min(.015,self.noise*3))
        if rms>threshold:
            self.heard=True;self.quiet=0
        else:
            self.quiet+=1
            if not self.heard:self.noise=.9*self.noise+.1*rms
        return (self.heard and self.quiet>=7) or (not self.heard and self.blocks>=30) or self.blocks>=80
