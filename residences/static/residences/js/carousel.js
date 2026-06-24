// Ce script gère le fonctionnement du carrousel de photos sur la page détail d'une unité.
// Il s'exécute une fois que la page est complètement chargée.
document.addEventListener('DOMContentLoaded', function () {

    // On cible le carrousel (il n'y en a qu'un par page détail, donc querySelector suffit)
    const carousel = document.querySelector('.carousel');

    // Si aucune unité n'a de carrousel sur cette page (ex: page sans photo), on arrête le script ici
    if (!carousel) return;

    // On récupère toutes les images et tous les points indicateurs à l'intérieur du carrousel
    const images = carousel.querySelectorAll('.carousel-img');
    const dots = carousel.querySelectorAll('.carousel-dot');
    const btnPrev = carousel.querySelector('.carousel-prev');
    const btnNext = carousel.querySelector('.carousel-next');

    // 'currentIndex' garde en mémoire quelle image est actuellement affichée
    let currentIndex = 0;

    // Fonction qui affiche l'image à l'index donné, et met à jour les points indicateurs
    function showImage(index) {
        // Retire la classe 'active' de toutes les images et de tous les points
        images.forEach(img => img.classList.remove('active'));
        dots.forEach(dot => dot.classList.remove('active'));

        // Ajoute la classe 'active' uniquement à l'image et au point correspondant à l'index demandé
        images[index].classList.add('active');
        if (dots[index]) {
            dots[index].classList.add('active');
        }

        currentIndex = index;
    }

    // Bouton "suivant" : passe à l'image suivante, ou revient à la première si on est à la fin
    if (btnNext) {
        btnNext.addEventListener('click', function () {
            const nextIndex = (currentIndex + 1) % images.length;
            showImage(nextIndex);
        });
    }

    // Bouton "précédent" : passe à l'image précédente, ou va à la dernière si on est au début
    if (btnPrev) {
        btnPrev.addEventListener('click', function () {
            const prevIndex = (currentIndex - 1 + images.length) % images.length;
            showImage(prevIndex);
        });
    }

    // Permet aussi de cliquer directement sur un point pour aller à cette photo précise
    dots.forEach(function (dot, index) {
        dot.addEventListener('click', function () {
            showImage(index);
        });
    });

});