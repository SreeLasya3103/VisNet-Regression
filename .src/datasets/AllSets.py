import torch
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
import os
from PIL import Image
import torchvision.transforms.functional as vfunc
import numpy
import csv
import glob

def resize_crop(img, img_dim):
    target_ratio = img_dim[0] / img_dim[1]
    ratio = img.size(1) / img.size(2)
    
    if ratio > target_ratio:
        img = vfunc.center_crop(img, (round(img.size(2)*target_ratio), img.size(2)))
    elif ratio < target_ratio:
        img = vfunc.center_crop(img, (img.size(1), round(img.size(1)/target_ratio)))
    
    img = vfunc.resize(img, img_dim, vfunc.InterpolationMode.BICUBIC, antialias=False)

    return img

def highpass_filter(img, mask_dim):
    orig_dim = (img.size(1), img.size(2))
    img = torch.fft.rfft2(img)
    img = torch.fft.fftshift(img)
    
    h_start = img.size(1)//2 - mask_dim[0]//2
    w_start = img.size(2)//2 - mask_dim[0]//2//2

    for i in range(h_start, h_start+mask_dim[0]):
        for j in range(w_start, w_start+mask_dim[1]//2):
            img[0][i][j] = 0

    img = torch.fft.ifftshift(img)    
    img = torch.fft.irfft2(img, orig_dim)
    
    return img

class ALL_reg(Dataset):
    def __init__(self, dataset_dir, set_type, img_dim, channels=3, cmap=None, grayscale_type='AVERAGE', mask_dim=None):
        self.files = []
        tmp_files = glob.glob(os.path.join(dataset_dir, 'SSF', set_type) + '/*.jpg')
        self.img_dim = img_dim
        self.cmap = cmap
        self.mask_dim = mask_dim
        self.channels = channels
        self.grayscale_type = grayscale_type
        self.labels_dict = {}
        tmp_labels_dict = {}
        
        with open(os.path.join(dataset_dir, 'SSF', 'label.csv'), mode='r') as infile:
            reader = csv.reader(infile)
            next(reader)
            tmp_labels_dict = {rows[0]:float(rows[7]) for rows in reader}


        tmp_files.sort()
        numpy.random.seed(37)
        numpy.random.shuffle(tmp_files)

        max_ten_plus = 0
        if set_type == 'train':
            max_ten_plus = 999999
        else:
            max_ten_plus = 999999

        ten_plus_count = 0
    
        for i in range(len(tmp_files)):
            img_path = tmp_files[i]
            dict_key = os.path.basename(img_path)[-19:]
            vis = torch.tensor([[tmp_labels_dict[dict_key]]])
            if vis >= 10.0:
                if ten_plus_count < max_ten_plus:
                    self.files.append(img_path)
                    self.labels_dict[img_path] = vis
                ten_plus_count = ten_plus_count + 1
            else:
                self.files.append(img_path)
                self.labels_dict[img_path] = vis
        
        tmp_files = glob.glob(os.path.join(dataset_dir, 'FROSI', set_type) + '/**/*.png', recursive=True)
        for i in range(len(tmp_files)):
            img_path = tmp_files[i]
            self.files.append(img_path)
            value = None
            if 'fog_50' in img_path:
                value = torch.Tensor([[0.031]])
            elif 'fog_100' in img_path:
                value = torch.Tensor([[0.062]])
            elif 'fog_150' in img_path:
                value = torch.Tensor([[0.093]])
            elif 'fog_200' in img_path:
                value = torch.Tensor([[0.124]])
            elif 'fog_250' in img_path:
                value = torch.Tensor([[0.155]])
            elif 'fog_300' in img_path:
                value = torch.Tensor([[0.186]])
            elif 'fog_400' in img_path:
                value = torch.Tensor([[0.249]])
            
            self.labels_dict[img_path] = value

        tmp_files = glob.glob(os.path.join(dataset_dir, 'FCS', set_type) + '/**/*.png', recursive=True)
        for i in range(len(tmp_files)):
            img_path = tmp_files[i]
            self.files.append(img_path)
            value = None
            if '0.02.png' in img_path:
                value = torch.Tensor([[0.093]])
            elif '0.01.png' in img_path:
                value = torch.Tensor([[0.186]])
            elif '0.005.png' in img_path:
                value = torch.Tensor([[0.373]])
            
            self.labels_dict[img_path] = value
        

        

        
    def __len__(self):
        return len(self.files)
            
    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        
        img_path = self.files[idx]
        value = torch.tensor([[self.labels_dict[img_path]]])
        
        orig = None
        pc = None
        fft = None
        
        orig = Image.open(img_path).convert('RGB')
        orig = transforms.PILToTensor()(orig)
        orig = resize_crop(orig, self.img_dim) / 255
        
        if self.cmap is not None:
            if self.grayscale_type == 'BLUE':
                pc = orig[2].detach().clone()
                pc = pc.view(1, *self.img_dim)
            elif self.grayscale_type == 'AVERAGE':
                pc = transforms.Grayscale()(orig)
            
            pc = self.cmap(pc)
            pc = torch.from_numpy(pc).permute((0, 3, 1, 2))
            pc = torch.cat((pc[0][0], pc[0][1], pc[0][2])).view(-1, *self.img_dim)
        
        if self.mask_dim is not None:
            if self.grayscale_type == 'BLUE':
                fft = orig[2].detach().clone()
                fft = fft.view(1, *self.img_dim)
            elif self.grayscale_type == 'AVERAGE':
                fft = transforms.Grayscale()(orig)
            
            fft = highpass_filter(fft, self.mask_dim)
            fft = torch.clamp(fft, 0.0, 1.0)
            if self.channels == 3:
                fft = self.cmap(fft)
                fft = torch.from_numpy(fft).permute((0, 3, 1, 2))
                fft = torch.cat((fft[0][0], fft[0][1], fft[0][2])).view(-1, *self.img_dim)
            
        if self.channels == 1:
            tf = transforms.Grayscale()
            orig = tf(orig)
            if pc is not None:
                pc = tf(pc)
        
        data = orig.view((1, 1, -1, *self.img_dim))
        if pc is not None:
            data = torch.cat((data, (pc.view((1, 1, -1, *self.img_dim)))))
        if fft is not None:
            data = torch.cat((data, (fft.view((1, 1, -1, *self.img_dim)))))
        
        return (data, value)
    
    @staticmethod
    def collate_fn(data):
        length = len(data)
        
        fft = None
        pc = None
        
        if data[0][0].size(0) > 2:
            fft = torch.cat([data[i][0][2] for i in range(length)])
        if data[0][0].size(0) > 1:
            pc = torch.cat([data[i][0][1] for i in range(length)])
        orig = torch.cat([data[i][0][0] for i in range(length)])
        values = torch.cat([data[i][1] for i in range(length)])
        
        if fft is not None:
            fft = fft.view((1, *fft.size()))
        if pc is not None:
            pc = pc.view((1, *pc.size()))
        orig = orig.view((1, *orig.size()))
        
        data = orig
        if pc is not None:
            data = torch.cat((data, pc))
        if fft is not None:
            data = torch.cat((data, fft))
        
        return (data, values)        

# class SSF_cls(Dataset):
#     def __init__(self, dataset_dir, set_type, img_dim, channels=3, cmap=None, grayscale_type='AVERAGE', mask_dim=None):
#         self.files = []
#         tmp_files = glob.glob(os.path.join(dataset_dir, set_type) + '/*.jpg')
#         self.img_dim = img_dim
#         self.cmap = cmap
#         self.mask_dim = mask_dim
#         self.channels = channels
#         self.grayscale_type = grayscale_type
#         self.labels_dict = None
        
#         with open(os.path.join(dataset_dir, 'label.csv'), mode='r') as infile:
#             reader = csv.reader(infile)
#             next(reader)
#             self.labels_dict = {rows[0]:float(rows[7]) for rows in reader}


#         tmp_files.sort()
#         numpy.random.seed(37)
#         numpy.random.shuffle(tmp_files)

#         max_ten_plus = 0
#         if set_type == 'train':
#             max_ten_plus = 250
#         else:
#             max_ten_plus = 100

#         ten_plus_count = 0
#         for i in range(len(tmp_files)):
#             img_path = tmp_files[i]
#             dict_key = os.path.basename(img_path)[-19:]
#             vis = torch.tensor([[self.labels_dict[dict_key]]])
#             if vis >= 10.0:
#                 if ten_plus_count < max_ten_plus:
#                     self.files.append(img_path)
#                 ten_plus_count = ten_plus_count + 1
#             else:
#                 self.files.append(img_path)

            
        
#     def __len__(self):
#         return len(self.files)
            
#     def __getitem__(self, idx):
#         if torch.is_tensor(idx):
#             idx = idx.tolist()
        
#         img_path = self.files[idx]
#         dict_key = os.path.basename(img_path)[-19:]
#         vis = torch.tensor([[self.labels_dict[dict_key]]])
#         value = torch.full((1,11), 0.0)
#         oneHot = 0
        
#         match vis:
#             case _ if vis < 1.0:
#                 oneHot = 0
#             case _ if vis < 2.0:
#                 oneHot = 1
#             case _ if vis < 3.0:
#                 oneHot = 2
#             case _ if vis < 4.0:
#                 oneHot = 3
#             case _ if vis < 5.0:
#                 oneHot = 4
#             case _ if vis < 6.0:
#                 oneHot = 5
#             case _ if vis < 7.0:
#                 oneHot = 6
#             case _ if vis < 8.0:
#                 oneHot = 7
#             case _ if vis < 9.0:
#                 oneHot = 8
#             case _ if vis < 10.0:
#                 oneHot = 9
#             case _ if vis >= 10.0:
#                 oneHot = 10
        
#         # match vis:
#         #     case _ if vis < 0.25:
#         #         oneHot = 0
#         #     case _ if vis < 0.375:
#         #         oneHot = 1
#         #     case _ if vis < 0.625:
#         #         oneHot = 2
#         #     case _ if vis < 0.875:
#         #         oneHot = 3
#         #     case _ if vis < 1.125:
#         #         oneHot = 4
#         #     case _ if vis < 1.375:
#         #         oneHot = 5
#         #     case _ if vis < 1.75:
#         #         oneHot = 6
#         #     case _ if vis < 2.25:
#         #         oneHot = 7
#         #     case _ if vis < 2.75:
#         #         oneHot = 8
#         #     case _ if vis < 3.5:
#         #         oneHot = 9
#         #     case _ if vis < 4.5:
#         #         oneHot = 10
#         #     case _ if vis < 6.0:
#         #         oneHot = 11
#         #     case _ if vis < 8.5:
#         #         oneHot = 12
#         #     case _ if vis <= 10.0:
#         #         oneHot = 13
#         #     case _ if vis > 10.0:
#         #         oneHot = 14
        
#         value[0][oneHot] = 1.0

#         orig = None
#         pc = None
#         fft = None
        
#         orig = Image.open(img_path).convert('RGB')
#         orig = transforms.PILToTensor()(orig)
#         orig = resize_crop(orig, self.img_dim) / 255
        
#         if self.cmap is not None:
#             if self.grayscale_type == 'BLUE':
#                 pc = orig[2].detach().clone()
#                 pc = pc.view(1, *self.img_dim)
#             elif self.grayscale_type == 'AVERAGE':
#                 pc = transforms.Grayscale()(orig)
            
#             pc = self.cmap(pc)
#             pc = torch.from_numpy(pc).permute((0, 3, 1, 2))
#             pc = torch.cat((pc[0][0], pc[0][1], pc[0][2])).view(-1, *self.img_dim)
        
#         if self.mask_dim is not None:
#             if self.grayscale_type == 'BLUE':
#                 fft = orig[2].detach().clone()
#                 fft = fft.view(1, *self.img_dim)
#             elif self.grayscale_type == 'AVERAGE':
#                 fft = transforms.Grayscale()(orig)
            
#             fft = highpass_filter(fft, self.mask_dim)
#             fft = torch.clamp(fft, 0.0, 1.0)
#             if self.channels == 3:
#                 fft = self.cmap(fft)
#                 fft = torch.from_numpy(fft).permute((0, 3, 1, 2))
#                 fft = torch.cat((fft[0][0], fft[0][1], fft[0][2])).view(-1, *self.img_dim)
            
#         if self.channels == 1:
#             tf = transforms.Grayscale()
#             orig = tf(orig)
#             if pc is not None:
#                 pc = tf(pc)
        
#         data = orig.view((1, 1, -1, *self.img_dim))
#         if pc is not None:
#             data = torch.cat((data, (pc.view((1, 1, -1, *self.img_dim)))))
#         if fft is not None:
#             data = torch.cat((data, (fft.view((1, 1, -1, *self.img_dim)))))
        
#         return (data, value)
    
#     @staticmethod
#     def collate_fn(data):
#         length = len(data)
        
#         fft = None
#         pc = None
        
#         if data[0][0].size(0) > 2:
#             fft = torch.cat([data[i][0][2] for i in range(length)])
#         if data[0][0].size(0) > 1:
#             pc = torch.cat([data[i][0][1] for i in range(length)])
#         orig = torch.cat([data[i][0][0] for i in range(length)])
#         values = torch.cat([data[i][1] for i in range(length)])
        
#         if fft is not None:
#             fft = fft.view((1, *fft.size()))
#         if pc is not None:
#             pc = pc.view((1, *pc.size()))
#         orig = orig.view((1, *orig.size()))
        
#         data = orig
#         if pc is not None:
#             data = torch.cat((data, pc))
#         if fft is not None:
#             data = torch.cat((data, fft))
        
#         return (data, values)        