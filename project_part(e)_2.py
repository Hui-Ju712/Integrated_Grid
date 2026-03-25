import numpy as np

#--Taking generation from PyPSA Model
g=np.array([10201.45,17832.07,10689.48,3993.98])

#--Taking Loads from PyPSA Model
l=np.array([14845,15471,9190,3210.98])

#--Calculate p_i
p_i=g-l
print(p_i)

#--Incidence matrix from PyPSA model topography
K_il=np.array([
    [1,1,1,0],
    [-1,0,0,1],
    [0,-1,0,0],
    [0,0,-1,-1]
]
)

#--Calculating Reactance and B matrix
Lengths=np.array([530,450,160,480])
X_line=0.1*Lengths
B_line=1/X_line
B = np.diag(B_line) 
print(B)

#--Calculating Laplacian
L_ij=K_il@B@K_il.T

#--Reducing order of Laplacian and inverting (tried both pinv and reduced order)

#L_ij_red= L_ij[1:, 1:]
#L_ji_red=np.linalg.inv(L_ij_red)

#n = L_ij.shape[0]
#L_ji = np.zeros((n, n))
#L_ji[1:, 1:] = L_ji_red
L_ji=np.linalg.pinv(L_ij)
print('L_ij=',L_ij)
print('L_ji=',L_ji)



#--Calculate PTDF
PTDF = B@K_il.T@L_ji
#print('\nPDTF=',PTDF)

#--Calculate p_l
p_l=PTDF@p_i
print('\n p_l=',p_l)

#--Alternative method using voltage angles (same result)
#theta = np.zeros(n)
#theta[1:] = np.linalg.solve(L_ij[1:, 1:], p_i[1:])
#p_l2 = B @ K_il.T @ theta

#print('\n p_l2=',p_l2)
