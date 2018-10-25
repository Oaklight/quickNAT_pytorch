import numpy as np
import torch
import quickNat_pytorch.data_utils as du

def dice_confusion_matrix(vol_output, ground_truth, num_classes):
    dice_cm = torch.zeros(num_classes,num_classes)
    batch_size, H, W = vol_output.size()
    for i in range(num_classes):
        GT = (ground_truth == i).float()
        for j in range(num_classes):
            Pred = (vol_output == j).float()
            inter = torch.sum(torch.mul(GT, Pred))
            union = torch.sum(GT) + torch.sum(Pred) + 0.0001
            dice_cm[i,j] = 2 * torch.div(inter, union)
            
    avg_dice = torch.mean(torch.diagflat(dice_cm))
    return avg_dice, dice_cm

def dice_score_perclass(vol_output, ground_truth, num_classes):
    dice_perclass = torch.zeros(num_classes)
    for i in range(num_classes):
        GT = (ground_truth == i).float()
        Pred = (vol_output == i).float()
        inter = torch.sum(torch.mul(GT, Pred))
        union = torch.sum(GT) + torch.sum(Pred) + 0.0001
        dice_perclass[i] = (2 * torch.div(inter, union))
    return dice_perclass

def evaluate_dice_score(model_path, num_classes, data_dir, label_dir, volumes_txt_file , remap_config, device = 0, logWriter = None):
    print("**Starting evaluation on the volumes. Please check tensorboard for dice score plots if a logWriter is provided in arguments**")
    print("Loading data volumes")
    volume_list, labelmap_list = du.load_and_preprocess(data_dir,label_dir,volumes_txt_file, orientation = 'COR', remap_config = 'Neo')
    print("Data loaded succssfully")
    
    with open(volumes_txt_file) as file_handle:
        volumes_to_use = file_handle.read().splitlines()
    
    batch_size = 5
    model = torch.load(model_path)
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        torch.cuda.empty_cache()
        model.cuda(device)    
        
    model.eval()
    
    volume_dice_score_list = []
    with torch.no_grad():    
        for vol_idx, (volume, labelmap) in enumerate(list(zip(volume_list, labelmap_list))):
            volume = volume if len(volume.shape) == 4 else volume[:,np.newaxis,:,:]
            volume, labelmap = torch.tensor(volume).type(torch.FloatTensor), torch.tensor(labelmap).type(torch.LongTensor)
            batch_dice_score_list = []
            for i in range(0, len(volume), batch_size):
                batch_x, batch_y = volume[i: i+batch_size], labelmap[i:i+batch_size]
                if cuda_available:
                    batch_x = batch_x.cuda(device)
                    batch_y = batch_y.cuda(device)
                out = model(batch_x)
                _, vol_output = torch.max(out, dim=1)
                dice_vector = dice_score_perclass(batch_x, batch_y, num_classes).cpu().numpy()
                batch_dice_score_list.append(dice_vector)
            volumne_dice_score = np.mean(batch_dice_score_list, 0)
            if logWriter:
                logWriter.plot_dice_score('eval_dice_score', volumne_dice_score, volumes_to_use[vol_idx], vol_idx)
            volume_dice_score_list.append(volumne_dice_score)    
            print("Volume "+str(vol_idx)+" evaluated")            
        avg_dice_score = np.mean(volume_dice_score_list, 0)    
        if logWriter:
            logWriter.plot_dice_score('average_eval_dice_score', avg_dice_score, 'Average Dice Score')       
        print("**End**") 
        
    return avg_dice_score, volume_dice_score_list


