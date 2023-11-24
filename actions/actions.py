import datetime as dt
import requests
import graphviz
import pandas as pd
from typing import Any, Text, Dict, List
from sklearn import tree
from sklearn.tree import DecisionTreeClassifier
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from swiplserver import PrologMQI
from rasa_sdk.events import SlotSet
from rasa_sdk.types import DomainDict
import warnings

EDAD_PERMITIDA = {
    "min": 0,
    "max": 100
}

class ActionDarHora(Action):
    
    def name(self) -> Text:
        return "action_tiempo"
    
    def run(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(text=f"{dt.datetime.now()}")

        return []
    
class ActionWithPrologCategoria(Action):
    def name(self) -> Text:
        return "action_categoria"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        categoria = tracker.get_slot('categoria')
        if categoria:
            categoria = str(categoria).title() 

            with PrologMQI(port=8000) as mqi:
                with mqi.create_thread() as prolog_thread:
                    prolog_thread.query("consult('/home/santiago/Documentos/Facu/Programacion Exploratoria/Prolog/categorias.pl')")

                    # Consultar la base de datos Prolog
                    query = f"categoria('{categoria}', ID)."
                    result = prolog_thread.query(query)

                    if result:
                        result_list = list(result)
                        id_categoria = result_list[0]["ID"]
                        dispatcher.utter_message(text=f"El ID de la categoría '{categoria}' es: {id_categoria}.")
                    else:
                        dispatcher.utter_message(text=f"No se encontró información para la categoría '{categoria}'.")
        else:
            dispatcher.utter_message(text="No se detectó una categoría válida en tu mensaje.")

        return []

class ActionMostrarCategorias(Action):
    def name(self) -> Text:
        return "action_muestra_categoria"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        with PrologMQI(port=8000) as mqi:
                with mqi.create_thread() as prolog_thread:
                    prolog_thread.query("consult('/home/santiago/Documentos/Facu/Programacion Exploratoria/Prolog/categorias.pl')")
                    categorias = list(prolog_thread.query(f"categoria(X, ID)."))
                    
                    if categorias:
                        respuesta = "Categorias y sus IDs:\n"
                        for categoria in categorias:
                            respuesta += f"- {categoria['X']} (ID: {categoria['ID']})\n"

                    dispatcher.utter_message(text=respuesta)
        return[]
    
class ActionSubCategorias(Action): #FALTA AGREGAR EL ID DE CADA SUBCATEGORIA
    def name(self) -> Text:
        return "action_subcategoria"
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        categoria= str((tracker.get_slot('categoria')).title())

        with PrologMQI(port=8000) as mqi:
                with mqi.create_thread() as prolog_thread:
                    prolog_thread.query("consult('/home/santiago/Documentos/Facu/Programacion Exploratoria/Prolog/categorias.pl')")  
                    verificacion = prolog_thread.query(f"categoria('{categoria}',ID).") #EL ID NO IMPORTA
                    
                    if verificacion: 
                        subcategorias = list(prolog_thread.query(f"es_subcategoria('{categoria}', Subcategoria)."))
                        
                        if subcategorias:
                            subcategorias_texto = "\n".join([sub['Subcategoria'] for sub in subcategorias])
                            respuesta = f"Subcategorías de {categoria}:\n{subcategorias_texto}"          
                        else:
                            respuesta = f"No se encontraron subcategorías para '{categoria}'."  
                    else:
                        respuesta = f"La categoria '{categoria}' no existe"
                dispatcher.utter_message(text=respuesta)   

        return []
    
class ActionBuscarProductosPorID(Action):
    def name(self) -> Text:
        return "action_buscar_productos_por_id"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        id_producto = next(tracker.get_latest_entity_values("id"), None)

        if id_producto:
            productos = self.buscar_productos_en_mercado_libre(id_producto)

            if productos:
                response_text = f"Productos con ID {id_producto} en Mercado Libre:\n"
                for producto in productos:
                    response_text += f"- {producto['title']} (Precio: ${producto['price']})\n"
                dispatcher.utter_message(text=response_text)
            else:
                dispatcher.utter_message(text=f"No se encontraron productos para el ID {id_producto}.")
        else:
            dispatcher.utter_message(text="No se detectó un ID de producto válido en tu mensaje.")

        return []

    def buscar_productos_en_mercado_libre(self, id_producto: Text) -> List[Dict[Text, Any]]:
        api_endpoint = f'https://api.mercadolibre.com/sites/MLA/search?category={id_producto}&limit=5'

        try:
            # Realizar la solicitud a la API de Mercado Libre
            response = requests.get(api_endpoint)

            if response.status_code == 200:
                # Si la solicitud es exitosa, obtener los títulos y precios de los productos
                products_data = response.json().get('results', [])
                productos_info = []
                for product in products_data:
                    title = product.get('title', 'Producto Desconocido')
                    price = product.get('price', 'Precio Desconocido')
                    productos_info.append({'title': title, 'price': price})
                return productos_info
            else:
                return []
        except requests.RequestException as e:
            print(f"Error en la solicitud HTTP: {str(e)}")
            return []
       
class ActionBuscarProductosPorNombre(Action):
    def name(self) -> Text:
        return "action_buscar_productos_por_nombre"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        producto = next(tracker.get_latest_entity_values("producto"), None)
        
        if producto:
            productos= self.buscar_productos_en_ml(producto)
        
            if productos:
                response_text = f"Productos con nombre {producto} en Mercado Libre:\n"
                for producto in productos:
                    response_text += f"- {producto['title']} (Precio: ${producto['price']})\n"
                dispatcher.utter_message(text=response_text)
            else:
                dispatcher.utter_message(text=f"No se encontraron productos para el ID {producto}.")
        else:
            dispatcher.utter_message(text="No se detectó un ID de producto válido en tu mensaje.")

        return []
            
            
    def buscar_productos_en_ml(self, producto: Text) -> List[Dict[Text, Any]]:
        api_endpoint = f'https://api.mercadolibre.com/sites/MLA/search?q={producto}&limit=10'

        try:
            # Realizar la solicitud a la API de Mercado Libre
            response = requests.get(api_endpoint)

            if response.status_code == 200:
                # Si la solicitud es exitosa, obtener los títulos y precios de los productos
                products_data = response.json().get('results', [])
                productos_info = []
                for product in products_data:
                    title = product.get('title', 'Producto Desconocido')
                    price = product.get('price', 'Precio Desconocido')
                    productos_info.append({'title': title, 'price': price})
                return productos_info
            else:
                return []
        except requests.RequestException as e:
            print(f"Error en la solicitud HTTP: {str(e)}")
            return []
        


class ActionRecomendacionCategoria(Action):
    def name(self) -> Text:
        return "action_recomendacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        edad = int(tracker.get_slot('edad'))
        sexo = tracker.get_slot('sexo').lower()
        
        min_edad = EDAD_PERMITIDA["min"]
        max_edad = EDAD_PERMITIDA["max"]
        
        
        if (edad==None):
            dispatcher.utter_message(text="No entiendo el año")
            return
        if (sexo==None):
            dispatcher.utter_message(text="No entiendo el sexo")
            return
        if not (min_edad <= edad <= max_edad):
            dispatcher.utter_message(text="Edad no válida")
            return {"edad": None}
        if sexo not in ["mujer", "hombre"]:
            dispatcher.utter_message(text="El valor de sexo debe ser 'mujer' o 'hombre'.")
            return {"sexo": None}
       

        warnings.filterwarnings("ignore")
        
        df = pd.read_csv("actions/data.csv")
        df = pd.get_dummies(data=df, drop_first=True)
        x = df.drop(columns='Gusto')
        y = df['Gusto']
        
        model = DecisionTreeClassifier(max_depth=5)
        model.fit(x,y)

        dot_data= tree.export_graphviz(model,out_file=None,
                                       feature_names=x.columns.tolist(),
                                       filled=True, rounded=True,
                                       special_characters=True)
        graph = graphviz.Source(dot_data)
        graph.render("arbolPreview")

        categorias = [
        "Joyas y Relojes",
        "Antiguedades y Colecciones",
        "Salud y Equipamiento Medico",
        "Electrodomesticos y Aires Acondicionados",
        "Construccion",
        "Bebes",
        "Computacion",
        "Herramientas",
        "Celulares y Telefonos",
        "Ropa y Accesorios",
        "Belleza y Cuidado Personal",
        "Consolas y Videojuegos",
        "Electronica, Audio y Video",
        "Juegos y Juguetes",
        "Deportes y Fitness",
        "Arte, Libreria y Merceria",
        "Hogar, Muebles y Jardin",
        "Autos, Motos y Otros",
        "Alimentos y Bebidas",
        "Camaras y Accesorios"
        ]
        
        if edad < 18:
            edad = 0
        elif 18 <= edad < 35:
            edad = 1
        elif 35 <= edad < 55:
            edad = 2
        else:
            edad = 3
            
        edad = str(edad)
        esHombre = "1" if sexo == "hombre" else "0"
        resultados = {}
        user_data = pd.DataFrame({
                "edad": [edad],
                "EsHombre": [esHombre],
            })
        
        for categoria in categorias:
            user_data[f"Categoria_{categoria}"] = 1
            for other_category in categorias:
                if other_category != categoria:
                    user_data[f"Categoria_{other_category}"] = 0
            pred = model.predict(user_data)
        
            if pred[0] == 1:
                resultados[categoria] = "Le va a gustar"
        
        for categoria, resultado in resultados.items():
            dispatcher.utter_message(text=f"Para la categoría '{categoria}': {resultado}")
        return[]
