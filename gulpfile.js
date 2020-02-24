// Load plugins
const autoprefixer  = require("gulp-autoprefixer");
//const browsersync   = require("browser-sync").create();
const cleanCSS      = require("gulp-clean-css");
const gulp = require("gulp");
const header = require("gulp-header");
const plumber = require("gulp-plumber");
const rename = require("gulp-rename");
const sass = require("gulp-sass");
const uglify = require("gulp-uglify");
const pkg = require('./package.json');
const sourcemaps = require('gulp-sourcemaps');
const concat = require('gulp-concat');

 

// Copy third party libraries from /node_modules into /vendor
gulp.task('vendor', function(cb) {

  // Bootstrap JS
  gulp.src([
      './node_modules/bootstrap/dist/js/*',
    ])
    .pipe(gulp.dest('./vendor/bootstrap/js'))
    
  // Bootstrap SCSS
  gulp.src([
      './node_modules/bootstrap/scss/**/*',
    ])
    .pipe(gulp.dest('./vendor/bootstrap/scss'))

  // ChartJS
  gulp.src([
      './node_modules/chart.js/dist/*.js'
    ])
    .pipe(gulp.dest('./vendor/chart.js'))

  // DataTables
  gulp.src([
      './node_modules/datatables.net/js/*.js',
      './node_modules/datatables.net-bs4/js/*.js',
      './node_modules/datatables.net-bs4/css/*.css'
    ])
    .pipe(gulp.dest('./vendor/datatables/'))

  // Font Awesome
  gulp.src([
      './node_modules/@fortawesome/**/*',
    ])
    .pipe(gulp.dest('./vendor'))

  // jQuery
  gulp.src([
      './node_modules/jquery/dist/*',
      '!./node_modules/jquery/dist/core.js'
    ])
    .pipe(gulp.dest('./vendor/jquery'))

  // jQuery Easing
  gulp.src([
      './node_modules/jquery.easing/*.js'
    ])
    .pipe(gulp.dest('./vendor/jquery-easing'))

  cb();

});

// CSS task
function css() {
  return   gulp.src('./src/sass/main.scss')
  .pipe(sourcemaps.init())
  .pipe(plumber())
  .pipe(sass({
    outputStyle: "compressed"
  }))
  .on("error", sass.logError)
  //.pipe(autoprefixer({
  //  browsers: ['last 2 versions'],
  //  cascade: false
  //}))  
  .pipe(gulp.dest('./dist/css'))
  .pipe(rename({
    suffix: ".min"
  }))
  .pipe(cleanCSS()) 
  .pipe(gulp.dest("./dist/css"))
  //.pipe(sourcemaps.write())
  .pipe(gulp.dest("./dist/css")) 
}






// JS task
function js() {
  return gulp
    .src([
      './src/js/plugins/jquery.min.js',
      './src/js/plugins/jquery.contextMenu.min.js',
      './src/js/plugins/jquery.ui.position.js',
      './src/js/plugins/popup.js',
      './src/js/plugins/moment.js', 
      './src/js/plugins/jquery.lazy.js', 
      './src/js/plugins/js.cookie.js', 
      './src/js/plugins/rainbowvis.js', 
      './src/js/plugins/popper.min.js', 
      './src/js/plugins/json-viewer.js', 
      './src/js/plugins/jquery.simulate.js',
      './src/js/plugins/jquery.scrollTo.js',
      './node_modules/bootstrap/dist/js/bootstrap.js',
      './src/js/plugins/bootstrap-multiselect.js',  
      './src/js/plugins/bootbox.js', 
      './src/js/plugins/bootstrap-datetimepicker.min.js', 
      './src/js/plugins/jquery-ui.js',
      './src/js/ui/json_viewer.js',
      './src/js/plugins/plotly.js'
    ])
    .pipe(concat('amscam.min.js').on('error', function(e){
        console.log('CONCAT ' + e);
    }))
    .pipe(gulp.dest('./dist/js')) 
    .pipe(uglify().on('error', function(e){
        console.log('CONCAT ' + e);
    })) 
    .pipe(gulp.dest('./dist/js'));
}



// API
function jsAPI() {
   return gulp
     .src([
       './tmp_APPS/src/js/framework/popper.min.js',
       './tmp_APPS/src/js/framework/jquery.min.js',
       './tmp_APPS/src/js/framework/bootstrap.js',
     ])
     .pipe(concat('allskytv.min.js').on('error', function(e){
         console.log('CONCAT ' + e);
     }))
     .pipe(gulp.dest('./tmp_APPS/dist/js')) 
     .pipe(uglify().on('error', function(e){
         console.log('CONCAT ' + e);
     })) 
     .pipe(gulp.dest('./dist/js'));
 }


 function cssAPI() {
   return   gulp.src('./tmp_APPS/src/sass/allskytv.scss')
   .pipe(sourcemaps.init())
   .pipe(plumber())
   .pipe(sass({
     outputStyle: "compressed"
   }))
   .on("error", sass.logError)
   //.pipe(autoprefixer({
   //  browsers: ['last 2 versions'],
   //  cascade: false
   //}))  
   .pipe(gulp.dest('./tmp_APPS/dist/css'))
   .pipe(rename({
     suffix: ".min"
   }))
   .pipe(cleanCSS()) 
   .pipe(gulp.dest("./tmp_APPS/dist/css"))
   //.pipe(sourcemaps.write())
   .pipe(gulp.dest("./tmp_APPS/dist/css")) 
 }




// Tasks
gulp.task("css", css);
gulp.task("js", js);
gulp.task("cssAPI", cssAPI); 
gulp.task("jsAPI", jsAPI); 


// JS task for BoostrapFileInput
function js_fileinput() {
  return gulp
    .src([
      './node_modules/bootstrap-fileinput/js/fileinput.js' 
    ])
    .pipe(concat('fileinput.min.js').on('error', function(e){
        console.log('CONCAT ' + e);
    }))
    .pipe(gulp.dest('./www/js')) 
    .pipe(uglify().on('error', function(e){
        console.log('CONCAT ' + e);
    })) 
    .pipe(gulp.dest('./www/js'));
}
gulp.task("js_fileinput", js_fileinput);


// CSS task for BoostrapFileInput
function css_fileinput() {
  return   gulp.src('./node_modules/bootstrap-fileinput/scss/fileinput.scss')
  .pipe(sourcemaps.init())
  .pipe(plumber())
  .pipe(sass({
    outputStyle: "compressed"
  }))
  .on("error", sass.logError)
  .pipe(autoprefixer({
    browsers: ['last 2 versions'],
    cascade: false
  }))  
  .pipe(gulp.dest('./www/css'))
  .pipe(rename({
    suffix: ".min"
  }))
  .pipe(cleanCSS()) 
  .pipe(gulp.dest("./www/css"))
  .pipe(sourcemaps.write())
  .pipe(gulp.dest("./www/css")) 
}
gulp.task("css_fileinput", css_fileinput);

// BrowserSync
function browserSync(done) {
  browsersync.init({
    server: {
      baseDir: "./"
    }
  });
  done();
}

// BrowserSync Reload
function browserSyncReload(done) {
  browsersync.reload();
  done();
}

// Watch files
function watchFiles() {
  gulp.watch("./scss/**/*", css);
  gulp.watch(["./js/**/*.js", "!./js/*.min.js"], js);
  gulp.watch("./**/*.html", browserSyncReload);
}

gulp.task("default", gulp.parallel(css, js));

// watch
gulp.task("dev", gulp.parallel(watchFiles, browserSync));
