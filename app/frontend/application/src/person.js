import {unpackDate} from "./formfunctions.js"
import {api} from "./global.js"


function getCacheFilename(filename) {
    var fileParts = filename.split('.')
    var cacheFilename = fileParts.slice(0, -1).join('.')
    cacheFilename += '_' + fileParts[fileParts.length - 1] + '.jpg'
    return cacheFilename
  }

export class Person{
    constructor(personJSON){
        this.id = personJSON.id
        this.firstName = personJSON.firstName
        this.middleName = (personJSON.middleName == null ? "" : personJSON.middleName)
        this.lastName = personJSON.lastName
        this.birthday = (personJSON.birthDay !== "not_allowed" ? unpackDate(new Date(personJSON.birthDay), personJSON.birthDateUnknowns)  : "")
        this.fileName = (personJSON.fileName == null ? "/blank-profile.png" :
                            (api + "upload/" + personJSON.fileName));
        this.cacheFileName = (personJSON.fileName == null ? "/blank-profile.png" :
                            (api + "upload/cache/" + getCacheFilename(personJSON.fileName)));
        this.maidenName = personJSON.maidenName
        this.birthPlace = personJSON.birthplace
        this.deathDay = (personJSON.isDead ? unpackDate(new Date(personJSON.deathDay), personJSON.deathDateUnknowns)
                            : null)
    }

    getFullName(){
        return(this.firstName + " " + this.middleName + " " + this.lastName)
    }

    getFirstName(){
        return(this.firstName)
    }

    getLastName(){
        return(this.lastName)
    }

    getBirthday(){
        return(this.birthday)
    }

    getFileName(){
        return(this.fileName)
    }

    getCachedFileName(){
        return(this.cacheFileName)
    }

    getID(){
        return(this.id)
    }

    getDeathDay(){
        return(this.deathDay)
    }

    getBirthPlace(){
        return(this.birthPlace)
    }

    getMaidenName(){
        return(this.maidenName)
    }
}