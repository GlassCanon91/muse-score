#%%
import requests 
from http.cookies import SimpleCookie
from bs4 import BeautifulSoup
import re
import json
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF, renderPM
from PyPDF2 import PdfFileMerger
import io
import os
from urllib.parse import urlparse
from fpdf import FPDF
from PIL import Image

from flask import Flask, request, render_template,send_file, make_response,Markup

def string_after(url_in,sign_in):
    return url_in[url_in.find(sign_in)+len(sign_in):]

s=requests.Session()

# url_sheet="https://musescore.com/user/31672114/scores/6613001"
api_url_raw="https://musescore.com/api/jmuse?id={x}&type={y}&index={z}&v2=1"
headers_set_image={"authorization":"8c022bdef45341074ce876ae57a48f64b86cdcf5"}
headers_set_mp3={"authorization":"63794e5461e4cfa046edfbdddfccc1ac16daffd2"}
#source :https://musescore.com/static/public/build/musescore_es6/202206/3780.da79906f50b94a8a0c05d3dcf0b4a461.js
headers_set_midi={"authorization": "38fb9efaae51b0c83b5bb5791a698b48292129e7"}
#source :https://musescore.com/static/public/build/musescore_es6/202206/1762.a9e6847a965d27c4ddbe2275971cb857.js

def write_pdf(list_url_pages_in):#,dir_location_in):
    merger = PdfFileMerger()
    file_numb=len(list_url_pages_in)
    count=0
    for url in list_url_pages_in:
        count+=1
        mem_pdf =  io.BytesIO()
        path=urlparse(url).path
        file_name=os.path.split(path)[1]
        with io.BytesIO(s.get(url).content) as open_file:
            #first case is svg type other case is png, ....
            if ".svg" in file_name:
                read_svg = svg2rlg(open_file)
                # renderPM.drawToFile(read_svg, "file.png", fmt="PNG") #generate png from csv file
                # with open("output.pdf", "wb") as f:  ##write as 1 page pdf
                #     f.write(mem_pdf.getbuffer())
                renderPDF.drawToFile(read_svg, mem_pdf)
                merger.append(mem_pdf)
            else :
                image = Image.open( open_file)
                im = image.convert('RGB')
                im.save(mem_pdf,format='pdf')
                merger.append(mem_pdf)

    mem_pdf_main =  io.BytesIO()
    merger.write(mem_pdf_main)
    mem_pdf_main.seek(0)
    return mem_pdf_main

def get_info_link(url_sheet_in):
    r1=s.get(url_sheet_in)
    soup1=BeautifulSoup(r1.content,'html5lib')
    tags_finded=soup1.find('div',attrs={"class":"js-store"})#find_all('div',attrs={"class":re.compile('js-.*')}
    pages_data_contain=tags_finded['data-content']
    pages_data_contain_json=json.loads( pages_data_contain)
    piece_id=pages_data_contain_json['store']['page']['data']['score']['id']
    page_numb=pages_data_contain_json['store']['page']['data']['score']['pages_count']
    file_name=pages_data_contain_json['store']['page']['data']['score']['title']
    try:
        file_name=''.join([c for c in file_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    except:
        file_name='sheet'
    
    return piece_id,page_numb,file_name
def get_image_link(url_sheet_in):
    piece_id,page_numb,file_name=get_info_link(url_sheet_in)
    api_url_list=[api_url_raw.format(x=piece_id,y='img',z=i) for i in range(page_numb)]
    url_pages=[]
    count=0
    for api_url in api_url_list :
        r_cache=s.get(api_url,headers=headers_set_image)
        url_page=r_cache.json() ['info']['url']
        url_pages.append(url_page)
        count+=1
        percent_now=float("{:.2f}".format(count/page_numb))*100
    return url_pages,file_name

def get_mp3_link(url_sheet_in):
    piece_id,page_numb,file_name=get_info_link(url_sheet_in)
    api_url=api_url_raw.format(x=piece_id,y='mp3',z='0')
    r_cache=s.get(api_url,headers=headers_set_mp3)
    url_page=r_cache.json() ['info']['url']
    mp3_byte = s.get(url_page).content
    return mp3_byte,file_name

def get_midi_link(url_sheet_in):
    piece_id,page_numb,file_name=get_info_link(url_sheet_in)
    api_url=api_url_raw.format(x=piece_id,y='midi',z='0')
    r_cache=s.get(api_url,headers=headers_set_midi)
    url_page=r_cache.json() ['info']['url']
    midi_byte = s.get(url_page).content
    return midi_byte,file_name
    
    
    


#-------------------------------------------
app = Flask(__name__)


@app.route('/favicon.ico')
def favicon_up():
    return app.send_static_file('images/favicon.ico')

@app.route('/')
def my_form():
    return render_template('my-form.html')


@app.route('/', methods=['POST'])
def my_form_post():
    return render_template('my-form.html')
    # return send_file(f'{file_name}.pdf', as_attachment=True)
    
    
@app.route('/result')
def result_form(name_label='',pages_label=''):
    text = request.args.get('url_input')
    errors=[]
    
    
    try:
        piece_id,page_numb,file_name=get_info_link(text)
        pages_label=f'Pages : {page_numb}'
        name_label=f'Name : {file_name}' 
        return render_template('result_success.html',name_piece=name_label,pages_number=pages_label)    
    except Exception as e:
            errors.append(
                "Unable to get URL. Please make sure it's valid musescore url and try again."
            )
            errors.append(str(e))
            return render_template('result_fail.html',errors=errors)#
        
        
@app.route('/result', methods=['POST'])
def downloader():
    text = request.args.get('url_input')
    button_name = request.form['download_button']
    # print(button_name)
    if button_name=='PDF download':
        list_url_pages,file_name=get_image_link(text)
        # print('MergingPdfFile:')
        pdf_main_object_file=write_pdf(list_url_pages)#,file_name
        response = make_response(pdf_main_object_file.read())
        response.headers.set('Content-Type', 'pdf')
        response.headers.set('Content-Disposition', 'attachment', filename=f'{file_name}.pdf')
        return response
    elif button_name=='MP3 download':
        # print('GetMp3File:')
        mp3_object_file,file_name=get_mp3_link(text)
        response = make_response(mp3_object_file)
        response.headers.set('Content-Type', 'audio/mpeg')
        response.headers.set('Content-Disposition', 'attachment', filename=f'{file_name}.mp3')
        return response
        
    elif button_name=='MIDI download':
        # print('GetMidiFile:')
        midi_object_file,file_name=get_midi_link(text)
        response = make_response(midi_object_file)
        response.headers.set('Content-Type', 'audio/midi')
        response.headers.set('Content-Disposition', 'attachment', filename=f'{file_name}.mid')
        return response
        
    else:
        return render_template('fata.html')
        

        
        

if __name__ == "__main__":
    app.run(debug=False)
    # app.run(debug=True,host='0.0.0.0',port=5000)


# %%
