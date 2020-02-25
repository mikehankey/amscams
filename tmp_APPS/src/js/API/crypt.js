var arcansa = "ALLONSENFANTSDELAPATRIE";

// ENCRYPT
function encrypt(msg) {
   var cipher = CryptoJS.AES.encrypt(msg, arcansa);
   return cipher.toString(); 
}

function decrypt()

// DECRYPT
var decipher = CryptoJS.AES.decrypt(cipher, arcansa);
decipher = decipher.toString(CryptoJS.enc.Utf8);
console.log(decipher);