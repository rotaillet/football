import pandas as pd
import numpy as np
import torch
from torch import nn, optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


df = pd.read_csv("merged_data.csv")
features = [
    'Possession_de_balle_home', 'Possession_de_balle_away',
    'Tirs_au_but_home', 'Tirs_au_but_away', 'Tirs_cadrés_home',
    'Tirs_cadrés_away', 'Tirs_non_cadrés_home', 'Tirs_non_cadrés_away',
    'Tirs_bloqués_home', 'Tirs_bloqués_away', 'Corners_home',
    'Corners_away', 'Sauvetages_du_gardien_home',
    'Sauvetages_du_gardien_away', 'Coup_francs_home', 'Coup_francs_away',
    'Hors-jeu_home', 'Hors-jeu_away', 'Fautes_home', 'Fautes_away',
    'Cartons_Jaunes_home', 'Cartons_Jaunes_away', 'Passes_home',
    'Passes_away', 'Cartons_Rouges_home', 'Cartons_Rouges_away',
    'score_mi_temps_home', 'score_mi_temps_away'
]

# Extraction des features
X = df[features].copy()

# Extraction du label (résultat) :
# 'resultat' vaut -1 si l'équipe 1 gagne, 0 en cas d'égalité et 1 si l'équipe 2 gagne.
# Pour l'entraînement avec CrossEntropyLoss, on mappe ces valeurs en 0, 1, 2.
y = df['resultat'].copy()
y = y.replace({-1: 0, 0: 1, 1: 2})

print(y.value_counts())


# Division train/test
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Normalisation des features
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)


# ----------------------------
# 2. Création du Dataset personnalisé
# ----------------------------

class FootballDataset(Dataset):
    def __init__(self, features, targets):
        self.features = torch.tensor(features, dtype=torch.float32)
        self.targets = torch.tensor(targets.values, dtype=torch.long)
        
    def __len__(self):
        return len(self.targets)
    
    def __getitem__(self, idx):
        return self.features[idx], self.targets[idx]

train_dataset = FootballDataset(X_train, y_train)
test_dataset = FootballDataset(X_test, y_test)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=16)

# ----------------------------
# 3. Définition du modèle avec PyTorch
# ----------------------------

class FootballNet(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, dropout_rate=0.5):
        super(FootballNet, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout_rate)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, output_dim)
        
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x




input_dim = len(features)
hidden_dim = 32
output_dim = 3  # Trois classes : victoire équipe 1, match nul, victoire équipe 2

model = FootballNet(input_dim, hidden_dim, output_dim)

# ----------------------------
# 4. Entraînement du modèle
# ----------------------------

criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.0001, weight_decay=1e-4)
num_epochs = 150
accur = []
for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    for batch_features, batch_targets in train_loader:
        optimizer.zero_grad()
        outputs = model(batch_features)
        loss = criterion(outputs, batch_targets)
        loss.backward()
        optimizer.step()
        running_loss += loss.item() * batch_features.size(0)
    
    epoch_loss = running_loss / len(train_dataset)
    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {epoch_loss:.4f}")
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_features, batch_targets in test_loader:
            outputs = model(batch_features)
            _, predicted = torch.max(outputs, 1)
            total += batch_targets.size(0)
            correct += (predicted == batch_targets).sum().item()
    accuracy = correct / total
    accur.append(accuracy)
    print(f"Test Accuracy: {accuracy*100:.2f}%")
print(max(accur))

# ----------------------------
# 5. Évaluation du modèle sur le jeu de test
# ----------------------------



