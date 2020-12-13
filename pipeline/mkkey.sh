openssl genrsa -out allsky.key 2048
openssl req -new -key allsky.key -out allsky.csr
openssl x509 -req -days 365 -in allsky.csr -signkey allsky.key -out allsky.crt
