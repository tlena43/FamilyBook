import { unpackDate } from "./formfunctions.js";
import { api } from "./global.js";

function getCacheFilename(filename) {
  const fileParts = filename.split(".");
  let cacheFilename = fileParts.slice(0, -1).join(".");
  cacheFilename += "_" + fileParts[fileParts.length - 1] + ".jpg";
  return cacheFilename;
}

export class Person {
  constructor(personJSON) {
    // defensive defaults so this doesn't explode if a field is missing
    const p = personJSON ?? {};

    this.id = p.id;
    this.firstName = p.firstName ?? "";
    this.middleName = p.middleName ?? "";
    this.lastName = p.lastName ?? "";
    this.parent1 = p.parent1 ?? "";
    this.parent2 = p.parent2 ?? "";
    this.spouse = p.spouse ?? "";

    this.birthday =
      p.birthDay && p.birthDay !== "not_allowed"
        ? unpackDate(new Date(p.birthDay), p.birthDateUnknowns)
        : "";

    // default profile image if no file
    if (!p.fileName) {
      this.fileName = "/blank-profile.png";
      this.cacheFileName = "/blank-profile.png";
    } else {
      this.fileName = api + "upload/" + p.fileName;
      this.cacheFileName = api + "upload/cache/" + getCacheFilename(p.fileName);
    }

    this.maidenName = p.maidenName ?? "";
    this.birthPlace = p.birthplace ?? "";

    this.deathDay =
      p.isDead && p.deathDay
        ? unpackDate(new Date(p.deathDay), p.deathDateUnknowns)
        : null;
  }

  getFullName() {
    return [this.firstName, this.middleName, this.lastName].filter(Boolean).join(" ");
  }

  getFirstName() {
    return this.firstName;
  }

  getLastName() {
    return this.lastName;
  }

  getBirthday() {
    return this.birthday;
  }

  getFileName() {
    return this.fileName;
  }

  getCachedFileName() {
    return this.cacheFileName;
  }

  getID() {
    return this.id;
  }

  getDeathDay() {
    return this.deathDay;
  }

  getBirthPlace() {
    return this.birthPlace;
  }

  getMaidenName() {
    return this.maidenName;
  }

  getParents(){
    return [this.parent1, this.parent2];
  }

  getSpouse(){
    return this.spouse;
  }

}