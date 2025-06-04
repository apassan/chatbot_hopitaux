import os
import re
from langchain_community.chat_models import ChatOpenAI
import pandas as pd
import csv
from dotenv import load_dotenv


class Appels_LLM:
    def __init__(self):
        load_dotenv()
        self.model = self.init_model()
        self.palmares_df = None
        self.etablissement_name=None
        self.specialty= None#Variable qui contient le nom de la spécialité dans la question de l'utilisateur
        self.ispublic= None#Variable qui contient le type d'établissement public/privé de la question de l'utilisateur
        self.city = None#Variable qui contient la ville de la question de l'utilisateur
        self.établissement_mentionné = None
        self.paths={
                "mapping_word_path":r"data\resultats_llm_v5.csv",
                "palmares_path":r"data\classments-hopitaux-cliniques-2024.xlsx",
                "coordonnees_path":r"data\fichier_hopitaux_avec_coordonnees_avec_privacitée.xlsx"
            }

        self.prompt={
                "get_speciality_prompt":
                """
            Voici un message pour lequel tu vas devoir choisir la spécialité qui correspond le plus. Voici mon message  :{prompt}.
            Voici une liste de spécialité pour laquelle tu vas devoir choisir la spécialité qui correspond le plus à mon message  : liste des spécialités: '{liste_spe}'? 

            Consignes:
            Si une seule spécialité de la liste correspond à ma demande, réponds UNIQUEMENT avec la spécialité exacte de la liste. 
            Exemple:  Pour le message 'Quel est le meilleur hôpital d'audition?', tu me répondras 'Audition'.
            Exemple:  Pour le message 'Je veux soigner mon AVC?', tu me répondras 'Accidents vasculaires cérébraux'.

            Si plusieurs spécialités de la liste peuvent correspondre ou sont liées à le message, réponds UNIQUEMENT avec les spécialités exactes de la liste et sous le format suivant: 'plusieurs correspondances: spécialité 1, spécialité 2'.
            Exemple: pour le message 'Je cherche un hôpital pour un accouchement', tu me répondras 'plusieurs correspondances: Accouchements à risques, Accouchements normaux'.
            Exemple: pour le message 'J'ai mal au genou', tu me répondras 'plusieurs correspondances: Prothèse de genou, Ligaments du genou'.

            Si aucune Spécialité de la liste est liée à ma demande, renvoie moi EXACTEMENT ces deux mots: 'aucune correspondance'
            N'invente pas de spécialité qui n'est pas dans la liste
            """
 
            ,

            "second_get_speciality_prompt":
            """
            Voici un message pour lequel tu vas devoir trouver la ou les pathologie(s) qui correspondent le plus: '{prompt}'
            Voici la liste des pathologies et des mots clés associés pour t'aider:{mapping_words}
            
            Si une seule spécialité de la liste correspond à ma demande, réponds UNIQUEMENT avec la spécialité exacte de la liste. 
            Exemple:  Pour le message 'Je veux soigner mon AVC?', tu me répondras 'Accidents vasculaires cérébraux'.

            Si plusieurs spécialités de la liste peuvent correspondre ou sont liées à le message, réponds UNIQUEMENT avec les spécialités exactes de la liste et sous le format suivant: 'plusieurs correspondances: spécialité 1, spécialité 2'.
            Exemple: pour le message 'Je cherche un hôpital pour un accouchement', tu me répondras 'plusieurs correspondances: Accouchements à risques, Accouchements normaux'.
            Exemple: pour le message 'J'ai mal au genou', tu me répondras 'plusieurs correspondances: Prothèse de genou, Ligaments du genou'.

            Si aucune Spécialité de la liste est liée à ma demande, renvoie moi EXACTEMENT ces deux mots: 'aucune correspondance'
            N'invente pas de spécialité qui n'est pas dans la liste
            """
            ,


            "get_offtopic_prompt":
            """
            Évaluez si le message suivant a un rapport avec la santé humaine ou les services de soins. 
           Si le message a un rapport avec le médical, retourne EXACTEMENT ce mot: 'Pertinent'.
           Par exemple pour le message: 'J'ai un cancer à Paris' , tu retourneras: 'Pertinent'.
           Par exemple pour le message: 'Cataracte' , tu retourneras: 'Pertinent'.
           Par exemple pour le message: 'J'ai mal aux pieds' , tu retourneras: 'Pertinent'.
           Par exemple pour le message: 'Les hôpitaux privés sont ils meilleurs que les publiques?' , tu retourneras: 'Pertinent'.

           Si le message est hors sujet et n'a aucun rapport avec le domaine médical, retourne EXACTEMENT ces deux mots: 'Hors sujet'. 
           Par exemple pour le message: 'Je mange des frites' , tu retourneras: 'Hors sujet'.
           Voici le Message : '{prompt}'
           """
           ,


           "get_offtopic_approfondi_prompt":
            """
        Tu es un chatbot assistant chargé de vérifier si une question d'un utilisateur est pertinente pour un classement annuel des hôpitaux.  
        Voici la question de l'utilisateur:'{prompt}'

        Une question est dite "pertinente" si elle concerne au moins un des cas suivants:
        - Une maladie, un symptôme ou une spécialité médicale  
        - Le classement des hôpitaux et cliniques  
        - La recherche d’un hôpital, d’une clinique ou d’un service médical  
        

        Si la question est pertinente, réponds uniquement par "pertinent".  
        Sinon, réponds uniquement par "hors sujet".  

        Exemples de questions pertinentes :  
        - Quel est la meilleur clinique de France ?
        - Conseille moi un hôpital à Lyon 
        - Je chercher un service de pneumologie
        - Où faire soigner mon glaucome ? 
        - Je veux corriger mon audition
        - Il y a fréquemment du sang dans mes urines. Conseille-moi un hôpital. 
        - Je veux cherche à faire soigner mes troubles bipôlaires
        - Est-ce que l'Institut mutualiste Montsouris est bon ?
        -Y a-t-il des hôpitaux privés avec un service de cardiologie interventionnelle ?

        Exemples de questions non pertinentes :  
        - Pourquoi les hôpitaux sont-ils en crise ?  #Il s'agit d'une demande d'information qui n'est pas dans le cadre direct de la recherche d'un établissement de soin
        - Dois-je prendre du paracétamol pour ma fièvre ? #Il s'agit d'une demande d'expertise médical qui n'est pas dans le cadre de la recherche d'un établissement de soin
        - Puis-je perdre la vue si j'ai un glaucome? #Il s'agit d'une demande d'expertise médical qui n'est pas dans le cadre de la recherche d'un établissement de soin

        

           """
           ,



           "get_city_prompt":
           
           """ Je vais te donner une phrase pour laquelle tu vas devoir déterminer si elle comporte un nom de ville qui peut porter à confusion. Voici la phrase '{prompt}'?
            Si une ville mentionnée dans la phrase peut porter confusion entre plusieurs villes françaises alors tu vas me renvoyer: 'confusion'.
            Si plusieurs villes en France portent ce nom, alors tu vas me renvoyer: 'confusion'.
            Par exemple:  pour la phrase, 'Soigne moi à Saint-Paul', tu me retourneras: 'confusion'.
            Par exemple:  pour la phrase, 'Quelle est la meilleure clinique privée de Montigny?', tu me retourneras: 'confusion'.
            Par exemple:  pour la phrase, 'Je suis à Valmont?', tu me retourneras: 'confusion'.                 

            Si aucune localisation n'est précisée , renvoie moi EXACTEMENT ce mot: 'correct'.
            Par exemple:  pour la phrase, 'Je veux soigner mon audition', tu me retourneras: 'correct'.
            
            Si une localisation est précisée et ne porte pas à confusion, renvoie moi EXACTEMENT ce mot: 'correct'.    
            Par exemple:  pour la phrase, 'Je veux un classement des meilleurs établissements de Reims', tu me retourneras: 'correct'.
            Par exemple:  pour la phrase, 'Quelle est la meilleur clinique Lyonnaise', tu me retourneras: 'correct'.
            
            Si la ville mentionnée n'est pas située en France, renvoie moi EXACTEMENT ces deux mots: 'ville étrangère'.
            Par exemple:  pour la phrase, 'Soigne moi dans une ville mexicaine', tu me retourneras: 'ville étrangère'. """
            ,



            "get_city_prompt_2":
            """ Quelle ville ou département est mentionné par la phrase suivante : '{prompt}'?
            Si une ville est mentionnée, réponds UNIQUEMENT avec le nom de ville.
            Par exemple:  pour la phrase, 'Trouve moi un hôpital à Lyon', tu me retourneras: 'Lyon'.

            Si un département est mentionné, réponds UNIQUEMENT avec le numéro du département.
            Par exemple:  pour la phrase, 'Je veux être hospitalisé dans le 92', tu me retourneras: '92'.               

            Si aucune localisation n'est mentionnée dans ma phrase, renvoie moi EXACTEMENT ces deux mots: 'aucune correspondance'.
            Par exemple:  pour la phrase, 'Je veux un classement des meilleurs établissements en France', tu me retourneras: 'aucune correspondance'.
            Par exemple:  pour la phrase, 'Quelle est la meilleur clinique pour une chirurgie à la montagne', tu me retourneras: 'aucune correspondance'."""
            ,


            "get_topk_prompt":
            """ Un numéro de classement est il mentionné dans la phrase suivante : '{prompt}'?
            Si un numéro de classement est mentionnée, réponds UNIQUEMENT avec le nombre associé.
            Par exemple: pour la phrase 'Quels sont les trois meilleurs hôpitaux pour soigner mon audition ?', tu me retourneras: '3'.

            Si aucune numéro de classement n'est mentionnée dans ma phrase, renvoie moi EXACTEMENT ces deux mots: 'non mentionné'.
            Par exemple:  pour la phrase, 'je veux un classement des meilleurs établissement en France', tu me retourneras: 'non mentionné'.

            Si la phrase inclue une expression comme 'le plus xxx' ou du superlatif qui implique implicitement une seule entité comme 'le meilleur', alors tu me retourneras '1'
            Par exemple: pour la phrase 'Quel est la meilleur clinique de Nantes?' ou 'Dis moi l'établissement le plus populaire de France' tu me retourneras: '1'.
            
            """,


            "is_public_or_private_prompt":
            """Un des noms exact de ma liste d'établissements est il mentionné précisément dans cette phrase: '{prompt}'? Voici ma liste d'établissements:
            {liste_etablissement}
            Réponds UNIQUEMENT avec le nom d'établissement exact de la liste si la phrase contient un des noms exacts d'établissement.
            Si aucun de ces établissement n'est mentionné dans ma phrase, renvoie moi EXACTEMENT ces deux mots: 'aucune correspondance'.
            Si la Ville de l'établissement est mentionnée mais pas le nom complet, par exemple 'Villeneuve-d’Ascq' est mentionné mais pas 'Clinique de Villeneuve-d’Ascq' alors tu renverras 'aucune correspondance'. 
            
            
            Voici des exemples sans noms d'établissement: pour la phrase 'Je cherche un hôpital pour soigner mon audition à Toulon ?' ou 'Quelle est la meilleure clinique de Limoges?', tu me répondras 'aucune correspondance'.
            Voici un exemple avec noms d'établissement: pour la phrase 'Est-ce que l'Hôpital Edouard-Herriot est bon en cas de problèmes auditifs ?' tu me répondras 'Hôpital Edouard-Herriot'. 
            """
            ,



            "is_public_or_private_prompt2" :
            """ Le type d'établissement de soin publique ou privé/clinique est il mentionné dans cette phrase : '{prompt}'?
            Si aucun type d'établissement n'est mentionné dans ma phrase, renvoie moi EXACTEMENT ces deux mots: 'aucune correspondance'.
            Si un type d'établissement est mentionné réponds UNIQUEMENT avec le mot 'Public' pour un établissement publique mentionné ou 'Privé' pour une clinique ou un établissement privé.""",


            "continuer_conv_prompt":
            """Vous êtes un assistant intelligent. Voici l'historique de la conversation précédente entre l'utilisateur et vous :{conv_history}
            Réponds au nouveau message de l'utilisateur:{prompt}"""
        
                
            }
        
        self.key_words=self.format_mapping_words_csv(self.paths["mapping_word_path"])
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def init_model(self) -> ChatOpenAI:
        api_key = os.getenv("API_KEY")

        # Initialise le modèle 
        self.model = ChatOpenAI(
            openai_api_key=api_key,
            model="gpt-4o-mini"
        )
        return self.model

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def format_mapping_words_csv(
        self, 
        file_path: str #fichier Excel des mots associés à chaque spécialité
        ) -> str:
        # Convertit le fichier Excel des mots associés à chaque spécialité en un format pour injection dans un prompt.
        df = pd.read_csv(file_path)
        colonne = df['Valeurs'].dropna()  # Nettoyage de base
        resultat = colonne.astype(str).str.cat(sep="\n")
        return resultat
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_specialty_list(self):
        #On récupère la liste des spécialités depuis le fichier excel qui liste les palmarès
        df_specialty = pd.read_excel(self.paths["palmares_path"] , sheet_name="Palmarès")
        self.palmares_df=df_specialty
        colonne_1 = df_specialty.iloc[:, 0].drop_duplicates()
        liste_spe = ", ".join(map(str, colonne_1.dropna()))
        return liste_spe
    
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def format_correspondance_list(self,
    liste_spe
        ):
       # Si on a plusieurs correspondances, on créer un texte avec la liste des corréspondances, en supprimant les doublons
        options_string = liste_spe.removeprefix("plusieurs correspondances:").strip()
        options_list = options_string.split(',')
        options_list = [element.replace('.', '') for element in options_list]
        options_list = [element.strip() for element in options_list]
        resultat = [element for element in options_list if element in liste_spe]
        self.specialty="plusieurs correspondances:"+",".join(resultat)
        return self.specialty

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    
    def get_speciality(self, 
    prompt: str #Question de l'utilisateur
    ) -> str:
        # Détermine la spécialité médicale correspondant à la question.

        liste_spe=self.get_specialty_list()
        #On fait appel au LLM pour déterminer la spécialité concernée
        get_speciality_prompt_formatted=self.prompt["get_speciality_prompt"].format(liste_spe=liste_spe,prompt=prompt)
        self.specialty = self.model.predict(get_speciality_prompt_formatted).strip()

        specialties = {
        "Maternités": ["Accouchements normaux", "Accouchements à risques"],
        "Cardiologie": ["Angioplastie coronaire", "Cardiologie interventionnelle", "Chirurgie cardiaque adulte", "Chirurgie cardiaque de l’enfant et de l’adolescent", "Infarctus du myocarde", "Insuffisance cardiaque", "Rythmologie"],
        "Veines et artères": ["Ablation des varices", "Chirurgie des artères", "Chirurgie des carotides", "Hypertension artérielle", "Médecine vasculaire"],
        "Orthopédie": ["Arthrose de la main", "Chirurgie de l'épaule", "Chirurgie de la cheville", "Chirurgie du canal carpien", "Chirurgie du dos de l'adulte", "Chirurgie du dos de l'enfant et de l’adolescent", "Chirurgie du pied", "Ligaments du genou", "Prothèse de genou", "Prothèse de hanche"],
        "Ophtalmologie": ["Cataracte", "Chirurgie de la cornée", "Chirurgie de la rétine", "Glaucome", "Strabisme"],
        "Gynécologie et cancers de la femme": ["Cancer de l'ovaire", "Cancer de l'utérus", "Cancer du sein", "Endométriose", "Fibrome utérin"],
        "Appareil digestif": ["Appendicite", "Cancer de l'estomac ou de l'œsophage", "Cancer du côlon ou de l'intestin", "Cancer du foie", "Cancer du pancréas", "Chirurgie de l'obésité", "Chirurgie du rectum", "Hernies de l'abdomen", "Maladies inflammatoires chroniques de l'intestin (MICI)", "Proctologie"],
        "Psychiatrie": ["Dépression", "Schizophrénie"],
        "Urologie": ["Adénome de la prostate", "Calculs urinaires", "Cancer de la prostate", "Cancer de la vessie", "Cancer du rein", "Chirurgie des testicules de l’adulte", "Chirurgie des testicules de l’enfant et de l’adolescent"],
        "Tête et cou": ["Amygdales et végétations", "Audition", "Cancer ORL", "Chirurgie dentaire et orale de l’adulte", "Chirurgie dentaire et orale de l’enfant et de l’adolescent", "Chirurgie du nez et des sinus", "Chirurgie maxillo-faciale", "Glandes salivaires"],
        "Neurologie": ["Accidents vasculaires cérébraux", "Epilepsie de l’adulte", "Epilepsie de l’enfant et de l’adolescent", "Maladie de Parkinson"],
        "Cancerologie": ["Cancer de la thyroïde", "Cancer des os de l’enfant et de l’adolescent", "Cancer du poumon", "Cancers de la peau", "Chirurgie des cancers osseux de l'adulte", "Chirurgie des sarcomes des tissus mous", "Leucémie de l'adulte", "Leucémie de l'enfant et de l’adolescent", "Lymphome-myélome de l’adulte", "Tumeurs du cerveau de l'adulte"],
        "Diabète": ["Diabète de l'adulte", "Diabète de l'enfant et de l’adolescent"]
    }
        if ',' in self.specialty and not self.specialty.startswith('plusieurs correspondances:'):
            self.specialty = 'plusieurs correspondances: ' + self.specialty
            
        

        if self.specialty.startswith("plusieurs correspondances:"):
            def get_specialty_keywords(message, specialties):
                for category, keywords in specialties.items():
                    if any(keyword.lower() in message.lower() for keyword in keywords):
                        return "plusieurs correspondances:"+f"{','.join(keywords)}"
            liste_spe= get_specialty_keywords(self.specialty, specialties)
            self.specialty=self.format_correspondance_list(liste_spe)
            return self.specialty
        else:
            if self.specialty == 'aucune correspondance':
                # Si on a aucune correspondance dans un premier temps, on va rappeler le llm en lui fournissant une liste de mots clés qui lui permettrait d'effectuer un matching
                mapping_words=self.key_words
                second_get_speciality_prompt_formatted=self.prompt["second_get_speciality_prompt"].format(prompt=prompt,mapping_words=mapping_words)
                self.specialty = self.model.predict(second_get_speciality_prompt_formatted).strip()
                return self.specialty
        return self.specialty

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_offtopic_approfondi(self, 
    prompt: str #Question de l'utilisateur
    ) -> str:
        # Détermine si la question est pertinente dans le cadre d'un assistant au palmarès des hôpitaux
        formatted_prompt=self.prompt["get_offtopic_approfondi_prompt"].format(prompt=prompt)
        res = self.model.predict(formatted_prompt).strip()
        return res
    
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_offtopic(self, 
    prompt: str #Question de l'utilisateur
    ) -> str:
        # Détermine si la question est hors sujet
        formatted_prompt=self.prompt["get_offtopic_prompt"].format(prompt=prompt)
        self.isofftopic = self.model.predict(formatted_prompt).strip()
        return self.isofftopic

   #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_city(self, 
    prompt: str #Question de l'utilisateur
    ) -> str:
        # Identifie la ville ou le département mentionné dans une phrase.

        #On va d'abord détecter via un appel llm si la ville peut comprter une ambiguité: homonymes en France, nom incomplet etc
        formatted_prompt = self.prompt["get_city_prompt"].format(prompt=prompt)
        self.city = self.model.predict(formatted_prompt).strip()

        #S'il n'y a pas d'ambiguité on va récupérer le nom de la ville dans un deuxième temps via un appel LLM
        if self.city=='correct':
            formatted_prompt = self.prompt["get_city_prompt_2"].format(prompt=prompt)
            self.city = self.model.predict(formatted_prompt).strip()
        return self.city

    #--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def get_topk(self, 
    prompt: str #Question de l'utilisateur
    ):
        # Identifie si le nombre d'établissements à afficher est mentionné dans la phrase de l'utilisateur.

        formatted_prompt = self.prompt["get_topk_prompt"].format(prompt=prompt)
        topk = self.model.predict(formatted_prompt).strip()
        if topk!='non mentionné':
            #On limite à 50 la liste d'établissmeents à afficher
            if int(topk)>50:
                topk='non mentionné'
            else:
                topk=int(topk)
        return topk
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    def get_etablissement_list(self):
        #Permet d'obtenir une liste formatée avec les établissements présent dans les classements
        coordonnees_df = pd.read_excel(self.paths["coordonnees_path"])#Ce df contient la liste des établissments
        colonne_1 = coordonnees_df.iloc[:, 0]
        liste_etablissement = [element.split(",")[0] for element in colonne_1]#On enlève toutes les localisations situées après les virgules qui pourraient fausser notre recherche de matchs
        liste_etablissement = list(set(liste_etablissement))
        liste_etablissement = [element for element in liste_etablissement if element != "CHU"]
        liste_etablissement = [element for element in liste_etablissement if element != "CH"]
        liste_etablissement = ", ".join(map(str, liste_etablissement))
        return liste_etablissement
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def is_public_or_private(self, 
    prompt: str #Question de l'utilisateur
    ) -> str:
        # Détermine si la question mentionne un hôpital publique,privé ou pas. Détermine aussi si un hôpital en particulier est mentionné

        #On va dans un premier temps lister les établissements des classements 
        liste_etablissement=self.get_etablissement_list()

        #On va ensuite appeler notre LLM qui va pouvoir détecter si l'un des établissements est mentionné dans la question de l'utilisateur
        formatted_prompt =self.prompt["is_public_or_private_prompt"].format(liste_etablissement=liste_etablissement,prompt=prompt) 
        self.etablissement_name = self.model.predict(formatted_prompt).strip()

  
        if self.etablissement_name in liste_etablissement:
            self.établissement_mentionné = True
            if self.établissement_mentionné:
                self.city='aucune correspondance'
            #On récupère la catégorie de cet établissment
            coordonnees_df = pd.read_excel(self.paths["coordonnees_path"])
            ligne_saut = coordonnees_df[coordonnees_df['Etablissement'].str.contains(self.etablissement_name,case=False, na=False)]
            self.ispublic = ligne_saut.iloc[0,4]
        else:
            #Si aucun établissement n'est détecté on va rechercher si un critère public/privé est mentionné
            formatted_prompt = self.prompt["is_public_or_private_prompt2"].format(prompt=prompt) 
            ispublic = self.model.predict(formatted_prompt).strip()
            self.établissement_mentionné = False
            self.ispublic = ispublic
        return self.ispublic
#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    def continuer_conv(self, 
    prompt: str ,#Question de l'utilisateur
    conv_history: list #historique de la conversation avec l'utilisateur
    ) -> str:
        # Réponds à la nouvelle question de l'utilisateur
        formatted_prompt = self.prompt["continuer_conv_prompt"].format(prompt=prompt,conv_history=conv_history) 
        self.newanswer  = self.model.predict(formatted_prompt).strip()
        return self.newanswer