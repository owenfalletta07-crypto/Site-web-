# TikTok motion design : NotPetya (2017)

Vidéo : `out/notpetya_tiktok.mp4` (1080x1920, 30 fps, H.264 High + AAC, 41,7 s, 15 scènes de 2,5 à 3 s).
Images de contrôle : `out/check/scene_XX.png` et `out/check/planche_contact.png` (zones TikTok en rouge).

Tout est fait en code : dessins en Python/PIL, beat synthétisé avec numpy. Aucune image, musique ni logo externe.
Seul élément externe : la police Anton (licence SIL Open Font), dans `assets/`.

```
python3 make_video.py check    # images de chaque scène + contrôle débordements/chevauchements
python3 make_video.py render   # rendu final MP4
```

## Script (une phrase par scène)

| # | Durée | Texte | Décor |
|---|---|---|---|
| 1 | 3,0 s | **10 milliards** de dégâts… à cause d'une **mise à jour**. | Coffre de banque, compteur qui monte, billets en fumée |
| 2 | 2,5 s | 27 juin 2017, en **Ukraine**. | Calendrier qui défile, drapeau ukrainien |
| 3 | 2,7 s | Un logiciel de **compta** très utilisé se met à jour. | Bureau, barre de progression |
| 4 | 2,8 s | Mais des hackers y ont caché un virus : **NotPetya**. | Repaire du hacker, virus qui saute dans le colis |
| 5 | 2,8 s | Il réclame une rançon… mais il **détruit tout**. | Écran de rançon qui clignote puis se fissure |
| 6 | 2,7 s | Le jour même, il frappe dans le **monde entier**. | Carte du monde, propagation |
| 7 | 2,9 s | Le géant Maersk : **76** terminaux portuaires à l'arrêt. | Port, grue figée, panneau STOP |
| 8 | 2,8 s | **45 000** PC et **4 000** serveurs à réinstaller. | Salle des serveurs, baies en domino |
| 9 | 2,7 s | Seul survivant : un serveur en **Afrique**. | Carte de l'Afrique, épingle |
| 10 | 2,7 s | Sauvé par… une **coupure** de courant ! | Lumière qui grésille puis noir, serveur endormi |
| 11 | 2,8 s | Sa copie part en **avion** pour tout reconstruire. | Ciel, avion de l'Afrique vers l'Europe |
| 12 | 2,9 s | Facture pour Maersk : jusqu'à **300 millions** de dollars. | Ticket qui se déroule, patron qui tourne de l'œil |
| 13 | 2,9 s | En 2018, Washington et Londres accusent l'armée **russe**. | Conférence de presse, flashs |
| 14 | 2,5 s | Moscou, elle, **dément**. | Silhouettes de coupoles, « Ce n'était pas nous. » |
| 15 | 3,0 s | Et **toi**, tu cliques encore sur « mettre à jour » ? | Popup OUI/NON, flèche vers les commentaires |

## Légende TikTok

> Un logiciel de compta, une mise à jour… et plus de 10 milliards de dollars de dégâts dans le monde 💥 Et Maersk, le géant du transport maritime, a été sauvé par une simple coupure de courant en Afrique. Tu cliques toujours sur « mettre à jour » sans réfléchir ? 👇
>
> #cybersécurité #hacking #histoirevraie #notpetya #apprendresurtiktok

## Vérification des faits (chaque point est confirmé par au moins 2 sources)

| Fait | Sources |
|---|---|
| Attaque le 27 juin 2017, visant d'abord l'Ukraine | Wikipedia (Petya), CCDCOE Cyber Law, SecurityAffairs (FedEx) |
| Propagation par une mise à jour piégée du logiciel de compta ukrainien M.E.Doc | Wikipedia, SecurityWeek (Cisco Talos), Tom's Hardware |
| Une fausse rançon : le programme détruit les données au lieu de les chiffrer de façon récupérable | Wikipedia, Wired/Greenberg (repris par tech2geek, Boing Boing) |
| Plus de 10 milliards de dollars de dégâts (estimation de la Maison-Blanche rapportée par Wired) | Wikipedia, Boing Boing (Wired), DNA Business |
| Maersk : 76 terminaux portuaires touchés | LRQA, Control Engineering |
| 45 000 PC et 4 000 serveurs réinstallés (+ 2 500 applications, en 10 jours) | SecurityWeek, SecurityAffairs, Hackread, ITPro |
| Un seul contrôleur de domaine survit en Afrique grâce à une coupure de courant, et sa copie part en avion vers l'Europe | Boing Boing (extrait Wired), Dark Reading (CISO de Maersk) |
| Coût pour Maersk : 200 à 300 M$ | CNBC, The Register, Threatpost |
| Fév. 2018 : les États-Unis et le Royaume-Uni attribuent l'attaque à l'armée russe ; la Russie dément | Defense One, CBS News, iTWire, Wikipedia |

Choix de prudence :
- **Ghana ou Lagos ?** Wired parle du Ghana (copie apportée à Maidenhead, au Royaume-Uni), le CISO de Maersk parle de Lagos et de Copenhague. La vidéo dit donc seulement « en Afrique » et « vers l'Europe », ce qui est vrai dans les deux versions.
- **45 000 ou 49 000 ?** Le président de Maersk, Jim Hagemann Snabe, a donné 45 000 PC. C'est ce chiffre officiel qui est retenu.
- **Pas de montant de rançon, pas de « 1/5 du commerce mondial » :** je n'ai pas pu les recouper sur 2 sources fiables, donc ils sont absents de la vidéo.

## Sources
- Wikipedia, Petya (malware family) : https://en.wikipedia.org/wiki/Petya_(malware_family)
- CCDCOE, NotPetya (2017) : https://cyberlaw.ccdcoe.org/wiki/NotPetya_(2017)
- Defense One, *White House Threatens 'Consequences' for 2017 Russian Cyber Attack* : https://www.defenseone.com/technology/2018/02/white-house-threatens-consequences-2017-notpetya-russian-cyber-attack/146046/
- CBS News, *U.S., U.K. blame Russian military for "destructive" cyberattack* : https://www.cbsnews.com/news/u-s-u-k-blame-russia-for-destructive-cyberattack-notpetya/
- iTWire, *UK formally blames Russia for NotPetya* : https://itwire.com/security/81770-uk-formally-blames-russia-for-notpetya-cyber-attack.html
- SecurityWeek, *Maersk Reinstalled 50,000 Computers After NotPetya Attack* : https://www.securityweek.com/maersk-reinstalled-50000-computers-after-notpetya-attack
- SecurityAffairs, *Maersk reinstalled 45,000 PCs and 4,000 servers* : https://securityaffairs.com/68227/security/maersk-notpetya-attack.html
- Hackread : https://www.hackread.com/notpetya-attack-maersk-reinstalled-45000-pcs-2500-apps-4000-servers/
- ITPro : https://www.itpro.com/cyber-attacks/30393/maersk-rebuilt-hefty-it-infrastructure-a-mere-10-days-after-notpetya-attack
- CNBC, *Maersk says June cyberattack could cost it up to $300 million* : https://www.cnbc.com/2017/08/16/maersk-says-notpetya-cyberattack-could-cost-300-million.html
- The Register : https://www.theregister.co.uk/2017/08/16/notpetya_ransomware_attack_cost_us_300m_says_shipping_giant_maersk
- Threatpost : https://threatpost.com/maersk-shippingreports-300m-loss-stemming-from-notpetya-attack/127477
- LRQA, *NotPetya ransomware attack on Maersk* : https://www.lrqa.com/en/insights/articles/notpetya-ransomware-attack-on-maersk-key-learnings/
- Control Engineering : https://www.controleng.com/throwback-attack-how-notpetya-accidentally-took-down-global-shipping-giant-maersk/
- Boing Boing (extrait de l'article Wired d'Andy Greenberg) : https://boingboing.net/2018/08/22/andy-greenberg.html
- Wired, *The Untold Story of NotPetya* (article d'origine) : https://www.wired.com/story/notpetya-cyberattack-ukraine-russia-code-crashed-the-world/
- Dark Reading, *Maersk CISO says NotPetya devastated several unnamed US firms* : https://www.darkreading.com/cyber-risk/maersk-ciso-says-notpeyta-devastated-several-unnamed-us-firms
- SecurityWeek, *NotPetya operators accessed M.E.Doc server using stolen credentials (Cisco)* : https://www.securityweek.com/notpetya-operators-accessed-medoc-server-using-stolen-credentials-cisco/
- Tom's Hardware : https://www.tomshardware.com/news/backdoored-automatic-updates-notpetya-ukraine,34956.html
