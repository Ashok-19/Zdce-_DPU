import torch
import torch.nn as nn
import torchvision
import torch.backends.cudnn as cudnn
import torch.optim
import os
import sys
import argparse
import time
import dataloader
import model
import Myloss
import numpy as np
from torchvision import transforms



def weights_init(m):
	classname = m.__class__.__name__
	if classname.find('Conv') != -1:
		m.weight.data.normal_(0.0, 0.02)
	elif classname.find('BatchNorm') != -1:
		m.weight.data.normal_(1.0, 0.02)
		m.bias.data.fill_(0)





def train(config):

	os.environ['CUDA_VISIBLE_DEVICES']='0'
	scale_factor = config.scale_factor
	DCE_net = model.enhance_net_nopool(scale_factor).cuda()

	# DCE_net.apply(weights_init)
	if config.load_pretrain == True:
		DCE_net.load_state_dict(torch.load(config.pretrain_dir))
	train_dataset = dataloader.lowlight_loader(config.lowlight_images_path)		
	
	train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=config.train_batch_size, shuffle=True, num_workers=config.num_workers, pin_memory=True)



	L_color = Myloss.L_color()
	L_spa = Myloss.L_spa()
	L_exp = Myloss.L_exp(16)
	# L_exp = Myloss.L_exp(16,0.6)
	L_TV = Myloss.L_TV()


	optimizer = torch.optim.Adam(DCE_net.parameters(), lr=config.lr, weight_decay=config.weight_decay)
	
	DCE_net.train()

	for epoch in range(config.num_epochs):
		for iteration, img_lowlight in enumerate(train_loader):

			img_lowlight = img_lowlight.cuda()

			E = 0.6

			enhanced_image,A  = DCE_net(img_lowlight)
			Loss_TV = 1600*L_TV(A)
			# Loss_TV = 200*L_TV(A)			
			loss_spa = torch.mean(L_spa(enhanced_image, img_lowlight))
			loss_col = 5*torch.mean(L_color(enhanced_image))

			loss_exp = 10*torch.mean(L_exp(enhanced_image,E))

			
			# best_loss
			loss =  Loss_TV + loss_spa + loss_col + loss_exp


			
			optimizer.zero_grad()
			loss.backward()

			'''

			total_norm = torch.norm(torch.stack([p.grad.norm(2) for p in DCE_net.parameters() if p.grad is not None])
						   , 2).item()
			print(f"Iteration {iteration+1} — Grad norm before clipping: {total_norm:.4f}")

			'''

			torch.nn.utils.clip_grad_norm(DCE_net.parameters(),config.grad_clip_norm)
			
			
			'''
			total_norm = torch.norm(torch.stack([p.grad.norm(2) for p in DCE_net.parameters() if p.grad is not None])
						   , 2).item()
			
			print(f"Iteration {iteration+1} — Grad norm after clipping: {total_norm:.4f}")
			'''
			optimizer.step()

			if ((iteration+1) % config.display_iter) == 0:
				print(f"Epoch {epoch} :Loss at iteration", iteration+1, ":", loss.item())
			if ((iteration+1) % config.snapshot_iter) == 0:

				torch.save(DCE_net.state_dict(), config.snapshots_folder + "Epoch" + str(epoch) + '.pth') 
				print(f'Model saved as Epoch{epoch}.pth')		




if __name__ == "__main__":

	parser = argparse.ArgumentParser()

	# Input Parameters
	parser.add_argument('--lowlight_images_path', type=str, default="data/train_data/")
	parser.add_argument('--lr', type=float, default=0.0001)
	parser.add_argument('--weight_decay', type=float, default=0.0001)
	parser.add_argument('--grad_clip_norm', type=float, default=0.1)
	parser.add_argument('--num_epochs', type=int, default=100)
	parser.add_argument('--train_batch_size', type=int, default=1)
	parser.add_argument('--val_batch_size', type=int, default=1)
	parser.add_argument('--num_workers', type=int, default=10)
	parser.add_argument('--display_iter', type=int, default=10)
	parser.add_argument('--snapshot_iter', type=int, default=10)
	parser.add_argument('--scale_factor', type=int, default=1)
	parser.add_argument('--snapshots_folder', type=str, default="snapshots_Zero_DCE++/")
	parser.add_argument('--load_pretrain', type=bool, default= True)
	parser.add_argument('--pretrain_dir', type=str, default= "snapshots_Zero_DCE++/2nd_train.pth")

	config = parser.parse_args()

	if not os.path.exists(config.snapshots_folder):
		os.mkdir(config.snapshots_folder)


	train(config)








	
