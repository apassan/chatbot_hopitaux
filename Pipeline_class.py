import os
import re
import pandas as pd
import csv
from Processing_class import Processing
from Appels_LLM_class import Appels_LLM


class Pipeline:
    def __init__(self):
        self.palmares_path=r"data\classments-hopitaux-cliniques-2024.xlsx"
        self.specialty= None#Variable qui contient le nom de la spécialité dans la question de l'utilisateur
        self.ispublic= None#Variable qui contient le type d'établissement public/privé de la question de l'utilisateur
        self.city = None#Variable qui contient la ville de la question de l'utilisateur
        self.no_city= None
        self.df_gen = None
        self.établissement_mentionné=None
        self.etablissement_name=None
        self.answer=Processing()
        self.appel_LLM=Appels_LLM()
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def reset_attributes(self):
        #Cette fonction réinitialise mes variables lorsque une nouvelle question est posée
        self.specialty = None
        self.ispublic = None
        self.city = None
        self.df_with_cities = None
        self.specialty_df = None
        self.no_city= None
        self.établissement_mentionné=None
        self.etablissement_name=None
        self.df_gen = None
        return None


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_infos_pipeline(self,
    prompt: str#question de l'utilisateur
    )->str:
            #Récupère les trois aspects clés de la question: la ville, l'aspect publique/privé et la spécialité médicale concernée
        if self.specialty is None:
            self.specialty=self.answer.specialty
        self.city=self.answer.city
        self.ispublic=self.answer.ispublic
        self.établissement_mentionné=self.answer.établissement_mentionné
        self.etablissement_name=self.answer.etablissement_name
        return self.specialty

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def from_prompt_to_ranking_df_with_distances(self, 
    prompt: str,  #Question de l'utilisateur
    excel_path: str,  #chemin du fichier palmarès
    )-> pd.DataFrame:
        # Trouve le classement des meilleurs hôpitaux correspondant aux critères de la question
        self.df_gen=self.answer.find_excel_sheet_with_privacy(prompt)
        self.get_infos_pipeline(prompt)
        if self.answer.classement_non_trouve:
                    return self.df_gen
        if self.answer.city == 'aucune correspondance':
            self.no_city= True
            return self.df_gen
        else :
            self.no_city= False
            self.answer.extract_loca_hospitals()
            df_with_distances=self.answer.get_df_with_distances()
            return df_with_distances

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


    def tableau_en_texte(self,
    df: pd.DataFrame,#Tableau des résultats correspondant à la question
    ):
        #convertit le tableau des résultats en une réponse sous forme de texte
        descriptions = []
        if self.no_city:
            for index, row in df.iterrows():
                description = (
                    f"{row['Etablissement']}:"
                    f"Un établissement {row['Catégorie']}. "
                    f"avec une note de {row['Note / 20']}"
                )
                descriptions.append(description)
            
            # Joindre toutes les descriptions avec des sauts de ligne
            texte_final = "<br>\n".join(descriptions)
            
            return texte_final
        else:  
            for index, row in df.iterrows():
                description = (
                    f"{row['Etablissement']}:"
                    f"Un établissement {row['Catégorie']} situé à {int(row['Distance'])} km. "
                    f"avec une note de {row['Note / 20']}"
                )
                descriptions.append(description)
            
            # Joindre toutes les descriptions avec des sauts de ligne
            texte_final = "<br>\n".join(descriptions)
            
            return texte_final

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_filtered_and_sorted_df(self, 
    df, #Dataframe avec les hôpitaux et leur distance
    rayon_max: int, # Rayon en km dans lequel on cherche des hôpitaux
    top_k: int,# Nombre d'hôpitaux qu'on cherche dans notre top
    prompt:str#Question de l'utilisateur
    ) -> str:
        #Filtre et trie le classement des hôpitaux, formate la réponse
        if self.établissement_mentionné==True:
            validity=False      
            if df['Etablissement'].str.contains(self.etablissement_name).any():
                validity=True
            if validity == False:
                if self.specialty=='aucune correspondance':
                    return f"Cet établissement ne fait pas partie des 50 meilleurs établissements du palmarès global"
                else: 
                    return f"Cet établissement n'est pas présent pour la pathologie {self.specialty}, vous pouvez cependant consulter le classement suivant:"
                
            df_sorted=df.sort_values(by='Note / 20', ascending=False).reset_index(drop=True)
            position = df_sorted.index[df_sorted["Etablissement"].str.contains(self.etablissement_name, case=False, na=False)][0] + 1  # +1 pour avoir une position humaine (1ère place au lieu de 0)
            descriptions = []
            for index, row in df_sorted.iterrows():
                description=row[['Etablissement','Catégorie','Note / 20']]
                        
                        # Joindre toutes les descriptions avec des sauts de ligne
                descriptions.append(str(description))
            texte_final = "<br>\n".join(descriptions)

            response=f"{self.etablissement_name} est classé n°{position} "
            if self.specialty=='aucune correspondance':
                response=response+f"du palmarès général"
                    
            else:
                response=response+f"du palmarès {self.specialty}."
            if self.ispublic!='aucune correspondance':
                        response=response+f" {self.ispublic}."
            return response


        filtered_df = df[df["Distance"] <= rayon_max]
        self.sorted_df = filtered_df.nlargest(top_k, "Note / 20")
        if self.sorted_df.shape[0] == top_k:
            res_str= self.tableau_en_texte(self.sorted_df)
            if self.specialty=='aucune correspondance':
                reponse=f"Voici les {top_k} meilleurs établissements du palmarès général dans un rayon de {rayon_max}km autour de {self.city}:\n{res_str}"
            else:
                reponse=f"Voici les {top_k} meilleurs établissements pour la pathologie: {self.specialty} dans un rayon de {rayon_max}km autour de {self.city}:\n{res_str}"
            
            self.answer.create_csv(question=prompt, reponse=reponse)
            return reponse
        
        elif rayon_max==500:
            res_str= self.tableau_en_texte(self.sorted_df)
            if self.specialty=='aucune correspondance':
                reponse=f"Voici les {self.sorted_df.shape[0]} meilleurs établissements au classement général dans un rayon de {rayon_max}km autour de {self.city}:<br>\n{res_str}"
            else:
                reponse=f"Voici les {self.sorted_df.shape[0]} meilleurs établissements pour la pathologie {self.specialty} dans un rayon de {rayon_max}km autour de {self.city}:<br>\n{res_str}"
            
            self.answer.create_csv(question=prompt, reponse=reponse)
            return reponse
        return None


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def final_answer(self, 
        prompt: str,  # Question de l'utilisateur
        top_k: int = 3,  # Nombre d'hôpitaux qu'on cherche dans notre top
        rayon_max: int = 50,  # Rayon en km dans lequel on cherche des hôpitaux
        specialty_st: str=None
        ) -> str:
        #reprend toutes les fonctions pour donner une réponse à partir de la question de l'utilisateur

        self.reset_attributes()
        self.specialty= specialty_st

        top_kbis =self.appel_LLM.get_topk(prompt)
        if top_kbis!='non mentionné':
            top_k=top_kbis

        if self.specialty is not None:
            self.answer.specialty= specialty_st
        else:
            self.answer.specialty= None
        relevant_file=self.palmares_path
        
        df = self.from_prompt_to_ranking_df_with_distances(prompt, relevant_file)
        if self.answer.geopy_problem:
            return "Dû à une surutilisation de l'API de Geopy, le service de calcul des distances est indisponible pour le moment, merci de réessayer plus tard ou de recommencer avec une question sans localisation spécifique "

        self.link=self.answer.lien_classement_web

        if self.answer.classement_non_trouve :
            if self.answer.ispublic=='Public':   
                return "Nous n'avons pas d'établissement publique pour cette pathologie, mais un classement des établissements privés existe. ", self.link
            elif self.answer.ispublic=='Privé': 
                return "Nous n'avons pas d'établissement privé pour cette pathologie, mais un classement des établissements publics existe. ", self.link

        if self.établissement_mentionné:
            res=self.get_filtered_and_sorted_df(df, rayon_max, top_k,prompt)
            return res, self.link
        


        if self.no_city== False:

            # Essaie avec rayon_max initial
            res = self.get_filtered_and_sorted_df(df, rayon_max, top_k,prompt)
            if res:
                return res, self.link

            # Si aucun résultat trouvé, essaie avec rayon_max augmenté (100 km)
            rayon_max2 = 100
            res = self.get_filtered_and_sorted_df(df, rayon_max2, top_k,prompt)
            if res:
                self.answer.create_csv(question=prompt, reponse=res)
                return res, self.link
             # Si aucun résultat trouvé, essaie avec rayon_max augmenté (200 km)
            rayon_max2 = 200
            res = self.get_filtered_and_sorted_df(df, rayon_max2, top_k,prompt)
            if res:
                self.answer.create_csv(question=prompt, reponse=res)
                return res, self.link

            # Si aucun résultat trouvé, essaie avec rayon_max augmenté à 500 km
            rayon_max3 = 500
            res=self.get_filtered_and_sorted_df(df, rayon_max3, top_k,prompt)
            self.answer.create_csv(question=prompt, reponse=res)
            return res, self.link
        
        else: 
            self.get_infos_pipeline(prompt)
            res_tab=self.df_gen.nlargest(top_k, "Note / 20")
            res_str = self.tableau_en_texte(res_tab)
            if top_k==1:
                res=f"Voici le meilleur établissement "
            else: 
                res=f"Voici les {top_k} meilleurs établissements "
            if self.specialty== 'aucune correspondance':
                res=res+f":<br> \n{res_str}"
            else:
                res=res+f"pour la pathologie {self.specialty}<br> \n{res_str}"
            return (res, self.link)

