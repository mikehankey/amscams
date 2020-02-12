// Load plugins
const autoprefixer  = require("gulp-autoprefixer"); 
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
      './src/js/plugins/jquery-3.4.1.min.js',
      './src/js/plugins/rainbowvis.js',
      './src/js/plugins/plotly.min.js',
      //'./src/js/eventviewer.js'
    ])
    .pipe(concat('allsky_eventviewer.min.js').on('error', function(e){
        console.log('CONCAT ' + e);
    }))
    .pipe(gulp.dest('./dist/js')) 
    .pipe(uglify().on('error', function(e){
        console.log('CONCAT ' + e);
    })) 
    .pipe(gulp.dest('./dist/js'));
}

// Tasks
gulp.task("css", css);
gulp.task("js", js);

 

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
