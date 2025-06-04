import streamlit as st
import sys
import os
from Pipeline_class import Pipeline
from Appels_LLM_class import Appels_LLM

#ici il reconnaît pas le terme pneumonie mais le reste marche

class StreamlitChatbot:
    def __init__(self):
        self.appel_LLM = Appels_LLM()
        self.MAX_MESSAGES = 4 

    def reset_session_state(self):
        """Réinitialise toutes les variables d'état de session."""
        # Réinitialiser la conversation

        # Réinitialiser les variables de sélection
        st.session_state.selected_option = None
        st.session_state.prompt = ""
        st.session_state.v_speciality= None
        st.session_state.ville= None
        st.session_state.slider_value=None
        st.session_state.v_spe = ""

    def reset_session_statebis(self):
        """Réinitialise toutes les variables d'état de session."""
        st.session_state.conversation = []
        self.answer_instance = Pipeline()
        self.appel_LLM = Appels_LLM()

        # Réinitialiser les variables de sélection
        st.session_state.selected_option = None
        st.session_state.prompt = ""
        st.session_state.v_speciality= None
        st.session_state.ville= None
        st.session_state.slider_value=None
        st.session_state.v_spe = ""
        # Réinitialiser d'autres variables potentielles si nécessaire
        
    def check_message_length(self,message):
        if len(message) > 200:
            self.reset_session_state()
            st.warning("Votre message est trop long. Merci de reformuler.")
            st.stop()

    def getofftopic(self,user_input):
        """Process user input and generate response."""
        isofftopic = self.appel_LLM.get_offtopic(user_input)
        if isofftopic == 'Hors sujet':
            self.reset_session_state()
            st.warning(
                "Je n'ai pas bien saisi la nature de votre demande. Merci de reformuler."
            )
            st.stop()
    
    def getofftopicapprofondi(self,user_input):
        """Process user input and generate response."""

        isofftopic = self.appel_LLM.get_offtopic_approfondi(user_input)
        if isofftopic == 'hors sujet':
            self.reset_session_state()
            st.warning(
                "Cet assistant a pour but de fournir des informations sur les classements des établissements de soins de cette année. Merci de reformuler."
            )
            st.stop()

    def check_conversation_limit(self):
        """Vérifie si la limite de messages est atteinte et réinitialise si nécessaire."""
        if len(st.session_state.conversation) >= self.MAX_MESSAGES:
            st.warning("La limite de messages a été atteinte. La conversation va redémarrer.")
            self.reset_session_statebis()
            st.rerun()
        
    def _display_conversation(self):
        """Display the conversation history with chat-like styling."""

        for user_msg, bot_msg in st.session_state.conversation:
            # User message
            st.chat_message("user").write(user_msg)
            # Bot message
            st.chat_message("assistant").write(bot_msg, unsafe_allow_html=True)
        
    def check_non_french_cities(self,user_input):
        self.city = self.appel_LLM.get_city(user_input)
        #st.write(self.city)
        if self.city == 'ville étrangère':
            self.reset_session_state()
            st.warning(
                f"Je ne peux pas répondre aux questions concernant les hôpitaux situés hors du territoire français, merci de consulter la page du palmarès. [🔗 Page du classement](https://www.lepoint.fr/hopitaux/classements)"
            )
            st.stop()
        if self.city == 'confusion':
            self.reset_session_state()
            st.warning(
                f"Je ne parviens pas à détecter votre localisation, merci de reformuler avec une autre ville."
            )
            st.stop()
    

    def run(self):
        st.title("🏥Assistant Hôpitaux")
        st.write("Posez votre question ci-dessous.")
         
        col1, col2, col3 = st.columns(3)
        # Display the questions inside containers
        with col1:
            # st.container(border=True)
            st.info("**Quel est le meilleur hôpital de France ?**")
        with col2:
            # st.container(border=True)
            st.info("**Y a-t-il des hôpitaux publics avec un service de proctologie dans la région Nantaise ?**")
        with col3:
            # st.container(border=True)
            st.info("**Est-ce que l'hôpital de la pitié salpétrière est un bon hôpital en cas de problèmes auditifs ?**")
        
        

        if st.sidebar.button("🔄 Démarrer une nouvelle conversation"):
            self.reset_session_statebis()
            st.rerun()
        # Initialisation de l'état de session
        if "conversation" not in st.session_state:
            st.session_state.conversation = []
        if "selected_option" not in st.session_state:
            st.session_state.selected_option = None
        if "prompt" not in st.session_state:
            st.session_state.prompt = ""
        if "v_spe" not in st.session_state:
            st.session_state.v_spe = ""
        
        self.check_conversation_limit()
        
        if len(st.session_state.conversation)==0  :

            # Entrée utilisateur
            user_input = st.chat_input("Votre message")
            

            if user_input:

                # Réinitialiser la session à chaque nouveau message
                self.reset_session_state()
                st.session_state.prompt = user_input
                self.check_message_length(st.session_state.prompt)
                self.getofftopic(st.session_state.prompt)
                self.getofftopicapprofondi(st.session_state.prompt)
                self.check_non_french_cities(st.session_state.prompt)
                

            if st.session_state.prompt:
                if st.session_state.v_spe == "":
                    v_speciality = self.appel_LLM.get_speciality(st.session_state.prompt)
                    st.session_state.v_spe = v_speciality

                if st.session_state.v_spe.startswith("plusieurs correspondances:"):
                        
                    # Extraire et afficher les options
                    options_string = st.session_state.v_spe.removeprefix("plusieurs correspondances:").strip()
                    options_list = options_string.split(',')
                    options_list = list(dict.fromkeys(options_list))

                    selected_option = st.radio(
                    "Précisez le domaine médical concerné :",
                    options=options_list,
                    index=None)
                                    


                    if selected_option is not None:
                        with st.spinner('Chargement'):
                            answer_instance = Pipeline()
                            res, link = answer_instance.final_answer(prompt=st.session_state.prompt, specialty_st=selected_option)
                            if res == 'établissement pas dans ce classement':
                                res= f"Cet hôpital n'est pas présent pour la spécialité {selected_option}"                  
                            
                        for links in link:
                            res=res+f"<br>[🔗Page du classement]({links})"
                        st.session_state.conversation.append((st.session_state.prompt, res))
                        
                        self.reset_session_state()
                        afficher = True
                        return None

                else:
                    with st.spinner('Chargement'):
                        answer_instance = Pipeline()
                        res, link = answer_instance.final_answer(prompt=st.session_state.prompt, specialty_st=v_speciality)
                    for links in link:
                        res=res+f"<br>[🔗Page du classement]({links})"
                    st.session_state.conversation.append((st.session_state.prompt, res))
                    self.reset_session_state()
                    afficher = True
                    return None
        else  :
            user_input = st.chat_input("Votre message")
            if user_input:
                with st.spinner('Chargement'):
                    res=self.appel_LLM.continuer_conv(prompt=user_input,conv_history=st.session_state.conversation)
                st.session_state.conversation.append((user_input, res))



def main():
    chatbot = StreamlitChatbot()
    chatbot.run()
    chatbot._display_conversation()
main()
