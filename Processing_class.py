import os
import re
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import time
import unicodedata
import csv
from datetime import datetime
from Appels_LLM_class import Appels_LLM



class Processing:
    def __init__(self):
        self.palmares_df = None
        self.appel_LLM=Appels_LLM()
        self.specialty_df = None
        self.etablissement_name=None
        self.classement_non_trouve=False
        self.lien_classement_web=None
        self.geopy_problem=False
        
        self.weblinks={
                "public":"https://www.lepoint.fr/hopitaux/classements/tableau-d-honneur-public.php",
                "privé":"https://www.lepoint.fr/hopitaux/classements/tableau-d-honneur-prive.php"
        }
        self.specialty= None#Variable qui contient le nom de la spécialité dans la question de l'utilisateur
        self.ispublic= None#Variable qui contient le type d'établissement public/privé de la question de l'utilisateur
        self.city = None#Variable qui contient la ville de la question de l'utilisateur
        self.df_with_cities = None
        self.établissement_mentionné = None
        self.paths={
                "mapping_word_path":r"data\resultats_llm_v5.csv",
                "palmares_path":r"data\classments-hopitaux-cliniques-2024.xlsx",
                "palmares_general_private_path":r"data\Tableaux_d'honneur_2024_PRIVE.csv",
                "palmares_general_public_path":r"data\Tableaux_d'honneur_2024_PUBLIC.csv",
                "coordonnees_path":r"data\fichier_hopitaux_avec_coordonnees_avec_privacitée.xlsx",
                "history_path":r"historique\results_history.csv"
            }
           
    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_infos(self,
    prompt: str#Question de l'utilisateur
    ) -> None:
        #Récupère les trois aspects clés de la question: la ville, l'aspect publique/privé et la spécialité médicale concernée
        if self.specialty is None:
            self.appel_LLM.get_speciality(prompt)
            self.palmares_df=pd.read_excel(self.paths["palmares_path"] , sheet_name="Palmarès")
            self.specialty=self.appel_LLM.specialty
        self.palmares_df=pd.read_excel(self.paths["palmares_path"] , sheet_name="Palmarès")
        self.appel_LLM.get_city(prompt)
        self.city=self.appel_LLM.city
        self.appel_LLM.is_public_or_private(prompt)
        self.établissement_mentionné = self.appel_LLM.établissement_mentionné
        self.etablissement_name=self.appel_LLM.etablissement_name
        self.ispublic=self.appel_LLM.ispublic
        return None


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def enlever_accents(self,
    chaine: str#chaîne pour laquelle on veut enlever les accents
    )-> str:
        chaine_normalisee = unicodedata.normalize('NFD', chaine)
        chaine_sans_accents = ''.join(c for c in chaine_normalisee if unicodedata.category(c) != 'Mn')
        chaine_sans_accents = chaine_sans_accents.replace("'", '-')
        return chaine_sans_accents

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _generate_lien_classement(self, 
    matching_rows: str = None, #On passe en paramètre les lignes de notre feuille "Palmarès" qui correspondent aux feuilles des classements qu'on veut récupérer
    ) -> str:
        #Cette fonction génère les liens des classements qu'on va suggérer à l'utilisateur
        self.lien_classement_web=[]
        if self.specialty== 'aucune correspondance':
            
            if self.ispublic == 'Public':
                self.lien_classement_web=[self.weblinks["public"]]
            elif self.ispublic == 'Privé':
                self.lien_classement_web=[self.weblinks["privé"]]
            else:
                self.lien_classement_web=[self.weblinks["public"],self.weblinks["privé"]]
            return None
        etat = self.ispublic
        if self.classement_non_trouve==True:
            if self.ispublic == 'Public':
                etat='prive'
            if self.ispublic == 'Privé':
                etat='public'
            lien_classement_web = self.specialty.replace(' ', '-')
            lien_classement_web='https://www.lepoint.fr/hopitaux/classements/'+ lien_classement_web + '-'+etat+'.php'
            lien_classement_web=lien_classement_web.lower()
            lien_classement_web=self.enlever_accents(lien_classement_web)
            self.lien_classement_web.append(lien_classement_web)
            return self.lien_classement_web

        for _, row in matching_rows.iterrows():
            lien_classement_web = row["Spécialité"].replace(' ', '-')
            lien_classement_web='https://www.lepoint.fr/hopitaux/classements/'+ lien_classement_web + '-'+row["Catégorie"] +'.php'
            lien_classement_web=lien_classement_web.lower()
            lien_classement_web=self.enlever_accents(lien_classement_web)
            self.lien_classement_web.append(lien_classement_web)
        return self.lien_classement_web
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def _load_and_transform_for_no_specialty(self, 
    category: str #catégorie public/privé des établissements que l'utilisateur souhaite récupérer
    ) -> pd.DataFrame:
    #Cette fonction récupère le bon tableau d'honneur (public et/ou privé) et le charge pour une question qui ne mentionne pas de pathologie
        if category== 'aucune correspondance':
            dfs=[]

            df_private=pd.read_csv(self.paths["palmares_general_private_path"] )
            df_private['Catégorie']='Privé'
            dfs.append(df_private)
            
            df_public=pd.read_csv(self.paths["palmares_general_public_path"] )
            df_public['Catégorie']='Public'
            dfs.append(df_public)

            df= pd.concat(dfs, join="inner", ignore_index=True)
        
        if category == 'Public':
            csv_path=self.paths["palmares_general_public_path"]
            df = pd.read_csv(csv_path)
            df['Catégorie'] = category
        elif category == 'Privé':
            csv_path=self.paths["palmares_general_private_path"]
            df = pd.read_csv(csv_path)
            df['Catégorie'] = category
        
        df = df.rename(columns={'Score final': 'Note / 20', 'Nom Print': 'Etablissement'})
        return df
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def load_excel_sheets(self, 
    matching_rows: pd.DataFrame, #On passe en paramètre les lignes de notre feuille "Palmarès" qui correspondent aux feuilles des classements qu'on veut récupérer
    ) -> pd.DataFrame:
        #Charge les feuilles Excel correspondantes aux matching_rows du Palmarès pour une question qui mentionne une pathologie
        excel_path = self.paths["palmares_path"] 

        dfs = []
        for _, row in matching_rows.iterrows():
            sheet_name = row.iloc[2]
            category = row["Catégorie"]
            df_sheet = pd.read_excel(self.paths["palmares_path"] , sheet_name=sheet_name)
            df_sheet["Catégorie"] = category
            dfs.append(df_sheet)

        if dfs:
            #Si on a trouvé une feuille
            return pd.concat(dfs, join="inner", ignore_index=True)
        else:
            if self.specialty!= 'aucune correspondance' and self.ispublic!='aucune correspondance':
                res=[]
                res.append("Nous n'avons pas d'établissement de ce type pour cette pathologie")
                self.classement_non_trouve=True
                return res
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


    def find_excel_sheet_with_speciality(self, 
    prompt: str,  #Question de l'utilisateur
    ) -> pd.DataFrame:
        
        # Trouve et charge les données Excel basées uniquement sur la spécialité si on a pas de critère publique/privé
        matching_rows = self.palmares_df[self.palmares_df["Spécialité"].str.contains(self.specialty, case=False, na=False)]
        self.lien_classement_web=[]
        self._generate_lien_classement(matching_rows)
        self.specialty_df = self.load_excel_sheets(matching_rows)
        return self.specialty_df

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def find_excel_sheet_with_privacy(self, 
    prompt: str, #Question de l'utilisateur
    ) -> pd.DataFrame:
    # Trouve et charge les données Excel en tenant compte de la spécialité et du type d'établissement.
        
        self.get_infos(prompt)
        specialty=self.specialty
        
        if specialty== 'aucune correspondance':
            self._generate_lien_classement()
            self.specialty_df=self._load_and_transform_for_no_specialty(category=self.ispublic)
            return self.specialty_df
        if self.ispublic == 'aucune correspondance':
            return self.find_excel_sheet_with_speciality(prompt)

        matching_rows = self.palmares_df[self.palmares_df["Spécialité"].str.contains(specialty, case=False, na=False)]
        matching_rows = matching_rows[matching_rows["Catégorie"].str.contains(self.ispublic, case=False, na=False)]
        self._generate_lien_classement(matching_rows)
        self.specialty_df = self.load_excel_sheets(matching_rows)
        return self.specialty_df



#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- 
    def extract_loca_hospitals(self, 
    df: pd.DataFrame = None #Dataframe contenant la feuille excel du classement des hôpitaux
    ) -> pd.DataFrame:
        # Récupère les noms de villes des Hôpitaux
        coordonnees_df = pd.read_excel(self.paths["coordonnees_path"]).dropna()
        notes_df = self.specialty_df
        coordonnees_df = coordonnees_df[["Etablissement", "Ville", "Latitude", "Longitude"]]
        notes_df = notes_df[["Etablissement", "Catégorie","Note / 20"]]
        self.df_with_cities = pd.merge(coordonnees_df, notes_df, on="Etablissement", how="inner")
        self.df_with_cities.rename(columns={"Ville": "City"}, inplace=True)
        return self.df_with_cities


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def exget_coordinates(self, 
    city_name: str #Ville de la question
    ) -> tuple:
    # Obtient les coordonnées géographiques de la ville de la question.

        try:
            geolocator = Nominatim(user_agent="city_distance_calculator")
            location = geolocator.geocode(city_name)
            if location:
                return (location.latitude, location.longitude)
            else:
                return None
        except Exception as e:
            self.geopy_problem=True
            return None
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def get_coordinates(self, 
    city_name: str #Ville de la liste d'hôpital
    ) -> tuple:
    # Obtient les coordonnées géographiques d'une ville de la liste des hôpitaux depuis ma feuille Hôpitaux
        df=self.df_with_cities
        result = df[df['City'] == city_name][['Latitude', 'Longitude']]
        latitude, longitude = result.iloc[0]
        return (latitude,longitude)
    

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_df_with_distances(self) -> pd.DataFrame:
    # Calcule les distances entre les hôpitaux et une ville donnée.
        query_coords = self.exget_coordinates(self.city)
        if self.geopy_problem:
            return None
           
        self.df_with_cities = self.df_with_cities.dropna(subset=['City'])

        def distance_to_query(city):
            city_coords = self.get_coordinates(city)
            if city_coords:
                try: 
                    res=geodesic(query_coords, city_coords).kilometers
                    return res
                except Exception as e:
                    self.geopy_problem=True
                    return None
            else:
                return None

        self.df_with_cities['Distance'] = self.df_with_cities['City'].apply(distance_to_query)
        self.df_with_distances = self.df_with_cities
        return self.df_with_distances

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


    def create_csv(self, 
    question:str,#Question de l'utilisateur
    reponse: str, #reponse à la question de l'utilisateur
    ):
        # On sauvegarde les requêtes dans un csv
        file_name=self.paths["history_path"]
        data = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "question": question,
            "ville": self.city,
            "type": self.ispublic,
            "spécialité": self.specialty,
            "résultat": reponse,
        }

        file_exists = os.path.exists(file_name)

        with open(file_name, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=data.keys())
            if not file_exists: 
                writer.writeheader()
            writer.writerow(data)
        return None




