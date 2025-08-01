import torch
import tomli
import sys
import os
ROOT_DIR = os.path.dirname(__file__)
sys.path.append(os.path.join(ROOT_DIR, 'datasets'))
import FoggyCityscapesDBF as fcs
import FROSI as frosi
import SSF as ssf
import SSF_YCbCr as ssf_YCbCr
import AllSets
import Jacobs
import Webcams
sys.path.append(os.path.join(ROOT_DIR, 'models'))
import Integrated
import RMEP as rmep
import VisNet
import Minimum
    
def main():
    f = open('config.toml', 'rb')
    config = tomli.load(f)

    try_cuda = True
    if 'try_cuda' in config:
        try_cuda = config['try_cuda']
    
    use_cuda = False
    if try_cuda:
        use_cuda = torch.cuda.is_available()
        if use_cuda:
            print('CUDA available. Using GPU...')
        else:
            print('CUDA unavailable. Using CPU...')
    else:
        print('Using CPU...')
        
    if config['mode'] == 'TRAIN':
        train(config, use_cuda)
    elif config['mode'] == 'TEST' or config['mode'] == 'VALIDATE':
        test(config, use_cuda)
    else:
        print('No mode specified!')
    
def train(config, use_cuda):
    model_module = None
    
    if config['model'] == 'VISNET':
        model_module = VisNet
    elif config['model'] == 'INTEGRATED':
        model_module = Integrated
    elif config['model'] == 'RMEP':
        model_module = rmep
    elif config['model'] == 'MINIM':
        model_module = Minimum
        
    dataset = None
    if config['dataset'] == 'FCS':
        dataset = fcs.FoggyCityscapesDBF
        model_module.train_classification(config, use_cuda, dataset)
    elif config['dataset'] == 'FROSI':
        dataset = frosi.FROSI
        model_module.train_classification(config, use_cuda, dataset)
    elif config['dataset'] == 'SSF':
        if config['numClasses'] == 1:
            dataset = ssf.SSF_reg
            model_module.train_regression(config, use_cuda, dataset)
        else:
            dataset = ssf.SSF_cls
            model_module.train_classification(config, use_cuda, dataset)
    elif config['dataset'] == 'WEBCAMS':
        dataset = Webcams.Webcams
        model_module.train_regression(config, use_cuda, dataset)
    elif config['dataset'] == 'SSF_YCbCr':
        if config['model'] != 'RMEP':
            print('YCbCr can only be used with RMEP')
            exit()
        dataset = ssf_YCbCr.SSF_reg
        model_module.train_regression(config, use_cuda, dataset)
    elif config['dataset'] == 'ALL':
        if config['numClasses'] == 1:
            dataset = AllSets.ALL_reg
            model_module.train_regression(config, use_cuda, dataset)
    elif config['dataset'] == 'JACOBS':
        if config['numClasses'] == 1:
            dataset = Jacobs.Jacobs
            model_module.train_regression(config, use_cuda, dataset)
    elif config['dataset'] == 'OTHER':
        dataset = None
        model_module.train_regression(config, use_cuda, dataset)
    
def test(config, use_cuda):
    model_module = None
    
    if config['model'] == 'VISNET':
        model_module = VisNet
    elif config['model'] == 'INTEGRATED':
        model_module = Integrated
    elif config['model'] == 'RMEP':
        model_module = rmep
    elif config['model'] == 'MINIM':
        model_module = Minimum
        
    dataset = None
    if config['dataset'] == 'FCS':
        dataset = fcs.FoggyCityscapesDBF
        model_module.test_classification(config, use_cuda, dataset)
    elif config['dataset'] == 'FROSI':
        dataset = frosi.FROSI
        model_module.test_classification(config, use_cuda, dataset)
    elif config['dataset'] == 'SSF':
        if config['numClasses'] == 1:
            dataset = ssf.SSF_reg
            model_module.test_regression(config, use_cuda, dataset)
        else:
            dataset = ssf.SSF_cls
            model_module.test_classification(config, use_cuda, dataset)
    elif config['dataset'] == 'WEBCAMS':
        dataset = Webcams.Webcams
        model_module.test_regression(config, use_cuda, dataset)
    elif config['dataset'] == 'SSF_YCbCr':
        if config['model'] != 'RMEP':
            print('YCbCr can only be used with RMEP')
            exit()
        dataset = ssf_YCbCr.SSF_reg
        model_module.test_regression(config, use_cuda, dataset)
    elif config['dataset'] == 'OTHER':
        dataset = None
        model_module.test_regression(config, use_cuda, dataset)


    
    

if __name__ == '__main__':
    main()
