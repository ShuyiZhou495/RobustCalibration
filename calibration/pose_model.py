import torch
from transforms import SE3
import numpy as np
from scipy.spatial.transform import Rotation

class Pose(torch.nn.Module):
    """
    extrinsic parameters
    """
    def __init__(self, opt, ext):
        super().__init__()
        # --- extrinsic parameters requiring gradient--- 
         
        self.t = torch.nn.Embedding(1, 3).cuda()
        self.R = torch.nn.Embedding(1, 3).cuda()
        torch.nn.init.zeros_(self.t.weight)
        torch.nn.init.zeros_(self.R.weight)

        # --- initial value ---
        self.correct = ext  #(6)

        error = torch.rand(6, dtype=torch.float, device="cuda")
        error /= torch.linalg.norm(error)

        self.init = self.correct.se3()
        
        self.init = self.correct.se3() + 0.1 # <- this is how we added error, but it might become invalid se3 depending on the value of initial "correct" extirnsic
        self.init = SE3(se3=self.init)
        
        self.init = SE3(se3=torch.ones(6).cuda().float() * 0.1) @ self.correct # <- this is a more reasonable way to apply error
        
        self.change = []


    def capture(self):
        torch.save((self.R.weight, self.t.weight, self.correct, self.init), "R.pth")

    def load(self):
        self.R.weight, self.t.weight, self.correct, self.init = torch.load("R.pth")

    def forward(self) -> torch.Tensor:
        ext = torch.cat((self.R.weight[0], self.t.weight[0]))
        return SE3(se3=ext) @ self.init

    @torch.no_grad
    def change_rate(self):
        ext = self.forward()
        t = np.array(ext.t.cpu().tolist())
        rot = ext.R.cpu().numpy()
        self.change.append([t, rot])
        if len(self.change) > 500:
            self.change.pop(0)
        return [np.linalg.norm((self.change[-1][0] - self.change[0][0]) / len(self.change)), 
                np.rad2deg(np.linalg.norm(Rotation.from_matrix(self.change[-1][1].transpose() @ self.change[0][1]).as_rotvec()))
                ]
    @property
    @torch.no_grad
    def get_error(self):
        error = self.correct.invert() @ self.forward()
        error_R = error.R.cpu().numpy()
        error_t = error.t.cpu().numpy()
        return Rotation.from_matrix(error_R).as_rotvec(degrees=True), error_t