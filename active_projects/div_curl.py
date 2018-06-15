from big_ol_pile_of_manim_imports import *

DEFAULT_SCALAR_FIELD_COLORS = [BLUE_E, GREEN, YELLOW, RED]

# Quick note to anyone coming to this file with the
# intent of recreating animations from the video.  Some
# of these, espeically those involving StreamLineAnimation,
# can take an extremely long time to run, but much of the
# computational cost is just for giving subtle little effects
# which don't matter too much.  Switching the line_anim_class
# to ShowPassingFlash will give significant speedups, as will
# increasing the values of delta_x and delta_y in sampling for
# the stream lines.  Certainly while developing, things were not
# run at production quality.


# Helper functions
def get_flow_start_points(x_min=-8, x_max=8,
                          y_min=-5, y_max=5,
                          delta_x=0.5, delta_y=0.5,
                          n_repeats=1,
                          noise_factor=None
                          ):
    if noise_factor is None:
        noise_factor = delta_y / 2
    return np.array([
        x * RIGHT + y * UP + noise_factor * np.random.random(3)
        for n in xrange(n_repeats)
        for x in np.arange(x_min, x_max + delta_x, delta_x)
        for y in np.arange(y_min, y_max + delta_y, delta_y)
    ])


def joukowsky_map(z):
    if z == 0:
        return 0
    return z + fdiv(1, z)


def inverse_joukowsky_map(w):
    u = 1 if w.real >= 0 else -1
    return (w + u * np.sqrt(w**2 - 4)) / 2


def derivative(func, dt=1e-7):
    return lambda z: (func(z + dt) - func(z)) / dt


def negative_gradient(potential_func, dt=1e-7):
    def result(p):
        output = potential_func(p)
        dx = dt * RIGHT
        dy = dt * UP
        dz = dt * OUT
        return -np.array([
            (potential_func(p + dx) - output) / dt,
            (potential_func(p + dy) - output) / dt,
            (potential_func(p + dz) - output) / dt,
        ])
    return result


def divergence(vector_func, dt=1e-7):
    def result(point):
        value = vector_func(point)
        return sum([
            (vector_func(point + dt * RIGHT) - value)[i] / dt
            for i, vect in enumerate([RIGHT, UP, OUT])
        ])
    return result


def two_d_curl(vector_func, dt=1e-7):
    def result(point):
        value = vector_func(point)
        return op.add(
            (vector_func(point + dt * RIGHT) - value)[1] / dt,
            -(vector_func(point + dt * UP) - value)[0] / dt,
        )
    return result


def cylinder_flow_vector_field(point, R=1, U=1):
    z = R3_to_complex(point)
    # return complex_to_R3(1.0 / derivative(joukowsky_map)(z))
    return complex_to_R3(derivative(joukowsky_map)(z).conjugate())


def cylinder_flow_magnitude_field(point):
    return np.linalg.norm(cylinder_flow_vector_field(point))


def get_colored_background_image(scalar_field_func,
                                 number_to_rgb_func,
                                 pixel_height=DEFAULT_PIXEL_HEIGHT,
                                 pixel_width=DEFAULT_PIXEL_WIDTH,
                                 ):
    ph = pixel_height
    pw = pixel_width
    fw = FRAME_WIDTH
    fh = FRAME_HEIGHT
    points_array = np.zeros((ph, pw, 3))
    x_array = np.linspace(-fw / 2, fw / 2, pw)
    x_array = x_array.reshape((1, len(x_array)))
    x_array = x_array.repeat(ph, axis=0)

    y_array = np.linspace(fh / 2, -fh / 2, ph)
    y_array = y_array.reshape((len(y_array), 1))
    y_array.repeat(pw, axis=1)
    points_array[:, :, 0] = x_array
    points_array[:, :, 1] = y_array
    scalars = np.apply_along_axis(scalar_field_func, 2, points_array)
    rgb_array = number_to_rgb_func(scalars.flatten()).reshape((ph, pw, 3))
    return Image.fromarray((rgb_array * 255).astype('uint8'))


def get_rgb_gradient_function(min_value=0, max_value=1,
                              colors=[BLUE, RED],
                              flip_alphas=True,  # Why?
                              ):
    rgbs = np.array(map(color_to_rgb, colors))

    def func(values):
        alphas = inverse_interpolate(min_value, max_value, values)
        alphas = np.clip(alphas, 0, 1)
        # if flip_alphas:
        #     alphas = 1 - alphas
        scaled_alphas = alphas * (len(rgbs) - 1)
        indices = scaled_alphas.astype(int)
        next_indices = np.clip(indices + 1, 0, len(rgbs) - 1)
        inter_alphas = scaled_alphas % 1
        inter_alphas = inter_alphas.repeat(3).reshape((len(indices), 3))
        result = interpolate(rgbs[indices], rgbs[next_indices], inter_alphas)
        return result

    return func


def get_color_field_image_file(scalar_func,
                               min_value=0, max_value=2,
                               colors=DEFAULT_SCALAR_FIELD_COLORS
                               ):
    # try_hash
    np.random.seed(0)
    sample_inputs = 5 * np.random.random(size=(10, 3)) - 10
    sample_outputs = np.apply_along_axis(scalar_func, 1, sample_inputs)
    func_hash = hash(
        str(min_value) + str(max_value) + str(colors) + str(sample_outputs)
    )
    file_name = "%d.png" % func_hash
    full_path = os.path.join(RASTER_IMAGE_DIR, file_name)
    if not os.path.exists(full_path):
        print "Rendering color field image " + str(func_hash)
        rgb_gradient_func = get_rgb_gradient_function(
            min_value=min_value,
            max_value=max_value,
            colors=colors
        )
        image = get_colored_background_image(scalar_func, rgb_gradient_func)
        image.save(full_path)
    return full_path


def vec_tex(s):
    return "\\vec{\\textbf{%s}}" % s


def four_swirls_function(point):
    x, y = point[:2]
    result = (y**3 - 4 * y) * RIGHT + (x**3 - 16 * x) * UP
    result *= 0.05
    norm = np.linalg.norm(result)
    if norm == 0:
        return result
    # result *= 2 * sigmoid(norm) / norm
    return result


def get_force_field_func(*point_strength_pairs, **kwargs):
    radius = kwargs.get("radius", 0.5)

    def func(point):
        result = np.array(ORIGIN)
        for center, strength in point_strength_pairs:
            to_center = center - point
            norm = np.linalg.norm(to_center)
            if norm == 0:
                continue
            elif norm < radius:
                to_center /= radius**3
            elif norm >= radius:
                to_center /= norm**3
            to_center *= -strength
            result += to_center
        return result
    return func


def get_charged_particles(color, sign, radius=0.1):
    result = Circle(
        stroke_color=WHITE,
        stroke_width=0.5,
        fill_color=color,
        fill_opacity=0.8,
        radius=radius
    )
    sign = TexMobject(sign)
    sign.set_stroke(WHITE, 1)
    sign.scale_to_fit_width(0.5 * result.get_width())
    sign.move_to(result)
    result.add(sign)
    return result


def get_proton(radius=0.1):
    return get_charged_particles(RED, "+", radius)


def get_electron(radius=0.05):
    return get_charged_particles(BLUE, "-", radius)


def preditor_prey_vector_field(point):
    x, y = point[:2]
    return -(y - 30) * RIGHT + (x - 30) * UP

# Mobjects


class StreamLines(VGroup):
    CONFIG = {
        "start_points_generator": get_flow_start_points,
        "start_points_generator_config": {},
        "dt": 0.05,
        "virtual_time": 3,
        "n_anchors_per_line": 100,
        "stroke_width": 1,
        "stroke_color": WHITE,
        "color_lines_by_magnitude": True,
        "min_magnitude": 0.5,
        "max_magnitude": 1.5,
        "colors": DEFAULT_SCALAR_FIELD_COLORS,
        "cutoff_norm": 15,
    }

    def __init__(self, func, **kwargs):
        VGroup.__init__(self, **kwargs)
        self.func = func
        dt = self.dt

        start_points = self.start_points_generator(
            **self.start_points_generator_config
        )
        for point in start_points:
            points = [point]
            for t in np.arange(0, self.virtual_time, dt):
                last_point = points[-1]
                points.append(last_point + dt * func(last_point))
                if np.linalg.norm(last_point) > self.cutoff_norm:
                    break
            line = VMobject()
            step = max(1, len(points) / self.n_anchors_per_line)
            line.set_points_smoothly(points[::step])
            self.add(line)

        self.set_stroke(self.stroke_color, self.stroke_width)

        if self.color_lines_by_magnitude:
            image_file = get_color_field_image_file(
                lambda p: np.linalg.norm(func(p)),
                min_value=self.min_magnitude,
                max_value=self.max_magnitude,
                colors=self.colors,
            )
            self.color_using_background_image(image_file)


class VectorField(VGroup):
    CONFIG = {
        "delta_x": 0.5,
        "delta_y": 0.5,
        "x_min": int(np.floor(-FRAME_WIDTH / 2)),
        "x_max": int(np.ceil(FRAME_WIDTH / 2)),
        "y_min": int(np.floor(-FRAME_HEIGHT / 2)),
        "y_max": int(np.ceil(FRAME_HEIGHT / 2)),
        "min_magnitude": 0,
        "max_magnitude": 2,
        "colors": DEFAULT_SCALAR_FIELD_COLORS,
        # Takes in actual norm, spits out displayed norm
        "length_func": lambda norm: 0.5 * sigmoid(norm),
        "stroke_color": BLACK,
        "stroke_width": 0.5,
        "fill_opacity": 1.0,
    }

    def __init__(self, func, **kwargs):
        VGroup.__init__(self, **kwargs)
        self.func = func
        self.rgb_gradient_function = get_rgb_gradient_function(
            self.min_magnitude,
            self.max_magnitude,
            self.colors,
            flip_alphas=False
        )
        for x in np.arange(self.x_min, self.x_max, self.delta_x):
            for y in np.arange(self.y_min, self.y_max, self.delta_y):
                point = x * RIGHT + y * UP
                self.add(self.get_vector(point))

    def get_vector(self, point):
        output = np.array(self.func(point))
        norm = np.linalg.norm(output)
        if norm == 0:
            output *= 0
        else:
            output *= self.length_func(norm) / norm
        vect = Vector(output)
        vect.shift(point)
        fill_color = rgb_to_color(
            self.rgb_gradient_function(np.array([norm]))[0]
        )
        vect.set_fill(fill_color, self.fill_opacity)
        vect.set_stroke(
            self.stroke_color,
            self.stroke_width
        )
        return vect


# Continual animations


class VectorFieldFlow(ContinualAnimation):
    CONFIG = {
        "mode": None,
    }

    def __init__(self, mobject, func, **kwargs):
        """
        Func should take in a vector in R3, and output a vector in R3
        """
        self.func = func
        ContinualAnimation.__init__(self, mobject, **kwargs)

    def update_mobject(self, dt):
        self.apply_nudge(dt)

    def apply_nudge(self, dt):
        self.mobject.shift(self.func(self.mobject.get_center()) * dt)


class VectorFieldSubmobjectFlow(VectorFieldFlow):
    def apply_nudge(self, dt):
        for submob in self.mobject:
            x, y = submob.get_center()[:2]
            if abs(x) < FRAME_WIDTH and abs(y) < FRAME_HEIGHT:
                submob.shift(self.func(submob.get_center()) * dt)


class VectorFieldPointFlow(VectorFieldFlow):
    def apply_nudge(self, dt):
        self.mobject.apply_function(
            lambda p: p + self.func(p) * dt
        )


# TODO: Make it so that you can have a group of streamlines
# varying in response to a changing vector field, and still
# animate the resulting flow
class ShowPassingFlashWithThinningStrokeWidth(AnimationGroup):
    CONFIG = {
        "n_segments": 10,
        "time_width": 0.1,
        "remover": True
    }

    def __init__(self, vmobject, **kwargs):
        digest_config(self, kwargs)
        max_stroke_width = vmobject.get_stroke_width()
        max_time_width = kwargs.pop("time_width", self.time_width)
        AnimationGroup.__init__(self, *[
            ShowPassingFlash(
                vmobject.deepcopy().set_stroke(width=stroke_width),
                time_width=time_width,
                **kwargs
            )
            for stroke_width, time_width in zip(
                np.linspace(0, max_stroke_width, self.n_segments),
                np.linspace(max_time_width, 0, self.n_segments)
            )
        ])


class StreamLineAnimation(ContinualAnimation):
    CONFIG = {
        "lag_range": 4,
        "line_anim_class": ShowPassingFlash,
        "line_anim_config": {
            "run_time": 4,
            "rate_func": None,
            "time_width": 0.3,
        },
    }

    def __init__(self, stream_lines, **kwargs):
        digest_config(self, kwargs)
        self.stream_lines = stream_lines
        group = VGroup()
        for line in stream_lines:
            line.anim = self.line_anim_class(line, **self.line_anim_config)
            line.time = -self.lag_range * random.random()
            group.add(line.anim.mobject)
        ContinualAnimation.__init__(self, group, **kwargs)

    def update_mobject(self, dt):
        stream_lines = self.stream_lines
        for line in stream_lines:
            line.time += dt
            adjusted_time = max(line.time, 0) % line.anim.run_time
            line.anim.update(adjusted_time / line.anim.run_time)


class JigglingSubmobjects(ContinualAnimation):
    CONFIG = {
        "amplitude": 0.05,
        "jiggles_per_second": 1,
    }

    def __init__(self, group, **kwargs):
        for submob in group.submobjects:
            submob.jiggling_direction = rotate_vector(
                RIGHT, np.random.random() * TAU,
            )
            submob.jiggling_phase = np.random.random() * TAU
        ContinualAnimation.__init__(self, group, **kwargs)

    def update_mobject(self, dt):
        for submob in self.mobject.submobjects:
            submob.jiggling_phase += dt * self.jiggles_per_second * TAU
            submob.shift(
                self.amplitude *
                submob.jiggling_direction *
                np.sin(submob.jiggling_phase) * dt
            )

# Scenes


class TestVectorField(Scene):
    CONFIG = {
        "func": cylinder_flow_vector_field,
        "flow_time": 15,
    }

    def construct(self):
        lines = StreamLines(
            four_swirls_function,
            virtual_time=3,
            min_magnitude=0,
            max_magnitude=2,
        )
        self.add(StreamLineAnimation(
            lines,
            line_anim_class=ShowPassingFlash
        ))
        self.wait(10)


class Introduction(Scene):
    CONFIG = {
        "production_quality_flow": True,
        "vector_field_func": cylinder_flow_vector_field,
    }

    def construct(self):
        self.add_plane()
        self.add_title()
        self.show_numbers()
        self.show_contour_lines()
        self.show_flow()
        self.apply_joukowsky_map()

    def add_plane(self):
        self.plane = ComplexPlane()
        self.plane.add_coordinates()
        self.plane.coordinate_labels.submobjects.pop(-1)
        self.add(self.plane)

    def add_title(self):
        title = TextMobject("Complex Plane")
        title.to_edge(UP, buff=MED_SMALL_BUFF)
        title.add_background_rectangle()
        self.title = title
        self.add(title)

    def show_numbers(self):
        run_time = 5

        unit_circle = self.unit_circle = Circle(
            radius=self.plane.unit_size,
            fill_color=BLACK,
            fill_opacity=0,
            stroke_color=YELLOW
        )
        dot = Dot()
        dot_update = UpdateFromFunc(
            dot, lambda d: d.move_to(unit_circle.point_from_proportion(1))
        )
        exp_tex = TexMobject("e^{", "0.00", "i}")
        zero = exp_tex.get_part_by_tex("0.00")
        zero.fade(1)
        exp_tex_update = UpdateFromFunc(
            exp_tex, lambda et: et.next_to(dot, UR, SMALL_BUFF)
        )
        exp_decimal = DecimalNumber(
            0, num_decimal_places=2,
            include_background_rectangle=True,
            color=YELLOW
        )
        exp_decimal.replace(zero)
        exp_decimal_update = ChangeDecimalToValue(
            exp_decimal, TAU,
            position_update_func=lambda mob: mob.move_to(zero),
            run_time=run_time,
        )

        sample_numbers = [
            complex(-5, 2),
            complex(2, 2),
            complex(3, 1),
            complex(-5, -2),
            complex(-4, 1),
        ]
        sample_labels = VGroup()
        for z in sample_numbers:
            sample_dot = Dot(self.plane.number_to_point(z))
            sample_label = DecimalNumber(
                z,
                num_decimal_places=0,
                include_background_rectangle=True,
            )
            sample_label.next_to(sample_dot, UR, SMALL_BUFF)
            sample_labels.add(VGroup(sample_dot, sample_label))

        self.play(
            ShowCreation(unit_circle, run_time=run_time),
            VFadeIn(exp_tex),
            UpdateFromAlphaFunc(
                exp_decimal,
                lambda ed, a: ed.set_fill(opacity=a)
            ),
            dot_update,
            exp_tex_update,
            exp_decimal_update,
            LaggedStart(
                FadeIn, sample_labels,
                remover=True,
                rate_func=there_and_back,
                run_time=run_time,
            )
        )
        self.play(
            FadeOut(exp_tex),
            FadeOut(exp_decimal),
            FadeOut(dot),
            unit_circle.set_fill, BLACK, {"opacity": 1},
        )
        self.wait()

    def show_contour_lines(self):
        warped_grid = self.warped_grid = self.get_warpable_grid()
        h_line = Line(3 * LEFT, 3 * RIGHT, color=WHITE)  # Hack
        func_label = self.get_func_label()

        self.remove(self.plane)
        self.add_foreground_mobjects(self.unit_circle, self.title)
        self.play(
            warped_grid.apply_complex_function, inverse_joukowsky_map,
            Animation(h_line, remover=True)
        )
        self.play(Write(func_label))
        self.add_foreground_mobjects(func_label)
        self.wait()

    def show_flow(self):
        stream_lines = self.get_stream_lines()
        stream_lines_copy = stream_lines.copy()
        stream_lines_copy.set_stroke(YELLOW, 1)
        stream_lines_animation = self.get_stream_lines_animation(
            stream_lines
        )

        tiny_buff = 0.0001
        v_lines = VGroup(*[
            Line(
                UP, ORIGIN,
                path_arc=0,
                n_arc_anchors=20,
            ).shift(x * RIGHT)
            for x in np.linspace(0, 1, 5)
        ])
        v_lines.match_background_image_file(stream_lines)
        fast_lines, slow_lines = [
            VGroup(*[
                v_lines.copy().next_to(point, vect, tiny_buff)
                for point, vect in it.product(h_points, [UP, DOWN])
            ])
            for h_points in [
                [0.5 * LEFT, 0.5 * RIGHT],
                [2 * LEFT, 2 * RIGHT],
            ]
        ]
        for lines in fast_lines, slow_lines:
            lines.apply_complex_function(inverse_joukowsky_map)

        self.add(stream_lines_animation)
        self.wait(7)
        self.play(
            ShowCreationThenDestruction(
                stream_lines_copy,
                submobject_mode="all_at_once",
                run_time=3,
            )
        )
        self.wait()
        self.play(ShowCreation(fast_lines))
        self.wait(2)
        self.play(ReplacementTransform(fast_lines, slow_lines))
        self.wait(3)
        self.play(
            FadeOut(slow_lines),
            VFadeOut(stream_lines_animation.mobject)
        )
        self.remove(stream_lines_animation)

    def apply_joukowsky_map(self):
        shift_val = 0.1 * LEFT + 0.2 * UP
        scale_factor = np.linalg.norm(RIGHT - shift_val)
        movers = VGroup(self.warped_grid, self.unit_circle)
        self.unit_circle.insert_n_anchor_points(50)

        stream_lines = self.get_stream_lines()
        stream_lines.scale(scale_factor)
        stream_lines.shift(shift_val)
        stream_lines.apply_complex_function(joukowsky_map)

        self.play(
            movers.scale, scale_factor,
            movers.shift, shift_val,
        )
        self.wait()
        self.play(
            movers.apply_complex_function, joukowsky_map,
            CircleThenFadeAround(self.func_label),
            run_time=2
        )
        self.add(self.get_stream_lines_animation(stream_lines))
        self.wait(20)

    # Helpers

    def get_func_label(self):
        func_label = self.func_label = TexMobject("f(z) = z + 1 / z")
        func_label.add_background_rectangle()
        func_label.next_to(self.title, DOWN, MED_SMALL_BUFF)
        return func_label

    def get_warpable_grid(self):
        top_grid = NumberPlane()
        top_grid.prepare_for_nonlinear_transform()
        bottom_grid = top_grid.copy()
        tiny_buff = 0.0001
        top_grid.next_to(ORIGIN, UP, buff=tiny_buff)
        bottom_grid.next_to(ORIGIN, DOWN, buff=tiny_buff)
        result = VGroup(top_grid, bottom_grid)
        result.add(*[
            Line(
                ORIGIN, FRAME_WIDTH * RIGHT / 2,
                color=WHITE,
                path_arc=0,
                n_arc_anchors=100,
            ).next_to(ORIGIN, vect, buff=2)
            for vect in LEFT, RIGHT
        ])
        # This line is a bit of a hack
        h_line = Line(LEFT, RIGHT, color=WHITE)
        h_line.set_points([LEFT, LEFT, RIGHT, RIGHT])
        h_line.scale(2)
        result.add(h_line)
        return result

    def get_stream_lines(self):
        func = self.vector_field_func
        if self.production_quality_flow:
            delta_x = 0.5
            delta_y = 0.1
        else:
            delta_x = 1
            # delta_y = 1
            delta_y = 0.1
        return StreamLines(
            func,
            start_points_generator_config={
                "x_min": -8,
                "x_max": -7,
                "y_min": -4,
                "y_max": 4,
                "delta_x": delta_x,
                "delta_y": delta_y,
                "n_repeats": 1,
                "noise_factor": 0.1,
            },
            stroke_width=2,
            virtual_time=15,
        )

    def get_stream_lines_animation(self, stream_lines):
        if self.production_quality_flow:
            line_anim_class = ShowPassingFlashWithThinningStrokeWidth
        else:
            line_anim_class = ShowPassingFlash
        return StreamLineAnimation(
            stream_lines,
            line_anim_class=line_anim_class,
        )


class ElectricField(Introduction, MovingCameraScene):
    def construct(self):
        self.add_plane()
        self.add_title()
        self.setup_warped_grid()
        self.show_uniform_field()
        self.show_moving_charges()
        self.show_field_lines()

    def setup_warped_grid(self):
        warped_grid = self.warped_grid = self.get_warpable_grid()
        warped_grid.save_state()
        func_label = self.get_func_label()
        unit_circle = self.unit_circle = Circle(
            radius=self.plane.unit_size,
            stroke_color=YELLOW,
            fill_color=BLACK,
            fill_opacity=1
        )

        self.add_foreground_mobjects(self.title, func_label, unit_circle)
        self.remove(self.plane)
        self.play(
            warped_grid.apply_complex_function, inverse_joukowsky_map,
        )
        self.wait()

    def show_uniform_field(self):
        vector_field = self.vector_field = VectorField(
            lambda p: UP,
            colors=[BLUE_E, WHITE, RED]
        )
        protons, electrons = groups = [
            VGroup(*[method(radius=0.2) for x in range(20)])
            for method in get_proton, get_electron
        ]
        for group in groups:
            group.arrange_submobjects(RIGHT, buff=MED_SMALL_BUFF)
            random.shuffle(group.submobjects)
        protons.next_to(FRAME_HEIGHT * DOWN / 2, DOWN)
        electrons.next_to(FRAME_HEIGHT * UP / 2, UP)

        self.play(
            self.warped_grid.restore,
            FadeOut(self.unit_circle),
            FadeOut(self.title),
            FadeOut(self.func_label),
            LaggedStart(GrowArrow, vector_field)
        )
        self.remove_foreground_mobjects(self.title, self.func_label)
        self.wait()
        for group, vect in (protons, UP), (electrons, DOWN):
            self.play(LaggedStart(
                ApplyMethod, group,
                lambda m: (m.shift, (FRAME_HEIGHT + 1) * vect),
                run_time=3,
                rate_func=rush_into
            ))

    def show_moving_charges(self):
        unit_circle = self.unit_circle

        protons = VGroup(*[
            get_proton().move_to(
                rotate_vector(0.275 * n * RIGHT, angle)
            )
            for n in range(4)
            for angle in np.arange(
                0, TAU, TAU / (6 * n) if n > 0 else TAU
            )
        ])
        jiggling_protons = JigglingSubmobjects(protons)
        electrons = VGroup(*[
            get_electron().move_to(
                proton.get_center() +
                proton.radius * rotate_vector(RIGHT, angle)
            )
            for proton in protons
            for angle in [np.random.random() * TAU]
        ])
        jiggling_electrons = JigglingSubmobjects(electrons)
        electrons.generate_target()
        for electron in electrons.target:
            y_part = electron.get_center()[1]
            if y_part > 0:
                electron.shift(2 * y_part * DOWN)

        # New vector field
        def new_electric_field(point):
            if np.linalg.norm(point) < 1:
                return ORIGIN
            vect = cylinder_flow_vector_field(point)
            return rotate_vector(vect, 90 * DEGREES)
        new_vector_field = VectorField(
            new_electric_field,
            colors=self.vector_field.colors
        )

        warped_grid = self.warped_grid

        self.play(GrowFromCenter(unit_circle))
        self.add(jiggling_protons, jiggling_electrons)
        self.add_foreground_mobjects(
            self.vector_field, unit_circle, protons, electrons
        )
        self.play(
            LaggedStart(VFadeIn, protons),
            LaggedStart(VFadeIn, electrons),
        )
        self.play(
            self.camera.frame.scale, 0.7,
            run_time=3
        )
        self.play(
            MoveToTarget(electrons),  # More indication?
            warped_grid.apply_complex_function, inverse_joukowsky_map,
            Transform(
                self.vector_field,
                new_vector_field
            ),
            run_time=3
        )
        self.wait(5)

    def show_field_lines(self):
        h_lines = VGroup(*[
            Line(
                5 * LEFT, 5 * RIGHT,
                path_arc=0,
                n_arc_anchors=50,
                stroke_color=LIGHT_GREY,
                stroke_width=2,
            ).shift(y * UP)
            for y in np.arange(-3, 3.25, 0.25)
            if y != 0
        ])
        h_lines.apply_complex_function(inverse_joukowsky_map)

        self.play(ShowCreation(
            h_lines,
            run_time=2,
            submobject_mode="all_at_once"
        ))
        for x in range(4):
            self.play(LaggedStart(
                ApplyMethod, h_lines,
                lambda m: (m.set_stroke, TEAL, 4),
                rate_func=there_and_back,
            ))


class AskQuestions(TeacherStudentsScene):
    def construct(self):
        div_tex = TexMobject("\\nabla \\cdot", vec_tex("v"))
        curl_tex = TexMobject("\\nabla \\times", vec_tex("v"))
        div_name = TextMobject("Divergence")
        curl_name = TextMobject("Curl")
        div = VGroup(div_name, div_tex)
        curl = VGroup(curl_name, curl_tex)
        for group in div, curl:
            group[1].set_color_by_tex(vec_tex("v"), YELLOW)
            group.arrange_submobjects(DOWN)
        topics = VGroup(div, curl)
        topics.arrange_submobjects(DOWN, buff=LARGE_BUFF)
        topics.move_to(self.hold_up_spot, DOWN)
        div.save_state()
        div.move_to(self.hold_up_spot, DOWN)
        screen = self.screen

        self.student_says(
            "What does fluid flow have \\\\ to do with electricity?",
            added_anims=[self.teacher.change, "happy"]
        )
        self.wait()
        self.student_says(
            "And you mentioned \\\\ complex numbers?",
            student_index=0,
        )
        self.wait(3)
        self.play(
            FadeInFromDown(div),
            self.teacher.change, "raise_right_hand",
            FadeOut(self.students[0].bubble),
            FadeOut(self.students[0].bubble.content),
            self.get_student_changes(*["pondering"] * 3)
        )
        self.play(
            FadeInFromDown(curl),
            div.restore
        )
        self.wait()
        self.look_at(self.screen)
        self.wait()
        self.change_all_student_modes("hooray", look_at_arg=screen)
        self.wait(3)

        topics.generate_target()
        topics.target.to_edge(LEFT, buff=LARGE_BUFF)
        arrow = TexMobject("\\leftrightarrow")
        arrow.scale(2)
        arrow.next_to(topics.target, RIGHT, buff=LARGE_BUFF)
        screen.next_to(arrow, RIGHT, LARGE_BUFF)
        complex_analysis = TextMobject("Complex analysis")
        complex_analysis.next_to(screen, UP)

        self.play(
            MoveToTarget(topics),
            self.get_student_changes(
                "confused", "sassy", "erm",
                look_at_arg=topics.target
            ),
            self.teacher.change, "pondering", screen
        )
        self.play(
            Write(arrow),
            FadeInFromDown(complex_analysis)
        )
        self.look_at(screen)
        self.wait(6)


class IntroduceVectorField(Scene):
    CONFIG = {
        "vector_field_config": {
            # "delta_x": 2,
            # "delta_y": 2,
            "delta_x": 0.5,
            "delta_y": 0.5,
        },
        "stream_line_config": {
            "start_points_generator_config": {
                # "delta_x": 1,
                # "delta_y": 1,
                "delta_x": 0.25,
                "delta_y": 0.25,
            },
            "virtual_time": 3,
        },
        "stream_line_animation_config": {
            # "line_anim_class": ShowPassingFlash,
            "line_anim_class": ShowPassingFlashWithThinningStrokeWidth,
        }
    }

    def construct(self):
        self.add_plane()
        self.add_title()
        self.points_to_vectors()
        self.show_fluid_flow()
        self.show_gravitational_force()
        self.show_magnetic_force()
        self.show_fluid_flow()

    def add_plane(self):
        plane = self.plane = NumberPlane()
        plane.add_coordinates()
        plane.remove(plane.coordinate_labels[-1])
        self.add(plane)

    def add_title(self):
        title = TextMobject("Vector field")
        title.scale(1.5)
        title.to_edge(UP, buff=MED_SMALL_BUFF)
        title.add_background_rectangle(opacity=1, buff=SMALL_BUFF)
        self.add_foreground_mobjects(title)

    def points_to_vectors(self):
        vector_field = self.vector_field = VectorField(
            four_swirls_function,
            **self.vector_field_config
        )
        dots = VGroup()
        for vector in vector_field:
            dot = Dot(radius=0.05)
            dot.move_to(vector.get_start())
            dot.target = vector
            dots.add(dot)

        self.play(LaggedStart(GrowFromCenter, dots))
        self.wait()
        self.play(LaggedStart(MoveToTarget, dots, remover=True))
        self.add(vector_field)
        self.wait()

    def show_fluid_flow(self):
        vector_field = self.vector_field
        stream_lines = StreamLines(
            vector_field.func,
            **self.stream_line_config
        )
        stream_line_animation = StreamLineAnimation(
            stream_lines,
            **self.stream_line_animation_config
        )

        self.add(stream_line_animation)
        self.play(
            vector_field.set_fill, {"opacity": 0.5}
        )
        self.wait(7)
        self.play(
            vector_field.set_fill, {"opacity": 1},
            VFadeOut(stream_line_animation.mobject),
        )
        self.remove(stream_line_animation)

    def show_gravitational_force(self):
        earth = self.earth = ImageMobject("earth")
        moon = self.moon = ImageMobject("moon", height=1)
        earth_center = 3 * RIGHT + 2 * UP
        moon_center = 3 * LEFT + DOWN
        earth.move_to(earth_center)
        moon.move_to(moon_center)

        gravity_func = get_force_field_func((earth_center, -6), (moon_center, -1))
        gravity_field = VectorField(
            gravity_func,
            **self.vector_field_config
        )

        self.add_foreground_mobjects(earth, moon)
        self.play(
            GrowFromCenter(earth),
            GrowFromCenter(moon),
            Transform(self.vector_field, gravity_field),
            run_time=2
        )
        self.vector_field.func = gravity_field.func
        self.wait()

    def show_magnetic_force(self):
        magnetic_func = get_force_field_func(
            (3 * LEFT, -1), (3 * RIGHT, +1)
        )
        magnetic_field = VectorField(
            magnetic_func,
            **self.vector_field_config
        )
        magnet = VGroup(*[
            Rectangle(
                width=3.5,
                height=1,
                stroke_width=0,
                fill_opacity=1,
                fill_color=color
            )
            for color in BLUE, RED
        ])
        magnet.arrange_submobjects(RIGHT, buff=0)
        for char, vect in ("S", LEFT), ("N", RIGHT):
            letter = TextMobject(char)
            edge = magnet.get_edge_center(vect)
            letter.next_to(edge, -vect, buff=MED_LARGE_BUFF)
            magnet.add(letter)

        self.add_foreground_mobjects(magnet)
        self.play(
            self.earth.scale, 0,
            self.moon.scale, 0,
            DrawBorderThenFill(magnet),
            Transform(self.vector_field, magnetic_field),
            run_time=2
        )
        self.vector_field.func = magnetic_field.func
        self.remove_foreground_mobjects(self.earth, self.moon)


class QuickNoteOnDrawingThese(TeacherStudentsScene):
    def construct(self):
        self.teacher_says(
            "Quick note on \\\\ drawing vector fields",
            bubble_kwargs={"width": 5, "height": 3},
            added_anims=[self.get_student_changes(
                "confused", "erm", "sassy"
            )]
        )
        self.look_at(self.screen)
        self.wait(3)


class ShorteningLongVectors(IntroduceVectorField):
    def construct(self):
        self.add_plane()
        self.add_title()
        self.contrast_adjusted_and_non_adjusted()

    def contrast_adjusted_and_non_adjusted(self):
        func = four_swirls_function
        unadjusted = VectorField(
            func, length_func=lambda n: n, colors=[WHITE],
        )
        adjusted = VectorField(func)
        for v1, v2 in zip(adjusted, unadjusted):
            v1.save_state()
            v1.target = v2

        self.add(adjusted)
        self.wait()
        self.play(LaggedStart(
            MoveToTarget, adjusted,
            run_time=3
        ))
        self.wait()
        self.play(LaggedStart(
            ApplyMethod, adjusted,
            lambda m: (m.restore,),
            run_time=3
        ))
        self.wait()


class TimeDependentVectorField(ExternallyAnimatedScene):
    pass


class ChangingElectricField(Scene):
    CONFIG = {
        "vector_field_config": {}
    }

    def construct(self):
        particles = self.get_particles()
        vector_field = self.get_vector_field()

        def update_vector_field(vector_field):
            new_field = self.get_vector_field()
            Transform(vector_field, new_field).update(1)
            vector_field.func = new_field.func

        def update_particles(particles, dt):
            func = vector_field.func
            for particle in particles:
                force = func(particle.get_center())
                particle.velocity += force * dt
                particle.shift(particle.velocity * dt)

        self.add(
            ContinualUpdateFromFunc(vector_field, update_vector_field),
            ContinualUpdateFromTimeFunc(particles, update_particles),
        )
        self.wait(20)

    def get_particles(self):
        particles = self.particles = VGroup()
        for n in range(9):
            if n % 2 == 0:
                particle = get_proton(radius=0.2)
                particle.charge = +1
            else:
                particle = get_electron(radius=0.2)
                particle.charge = -1
            particle.velocity = np.random.normal(0, 0.1, 3)
            particles.add(particle)
            particle.shift(np.random.normal(0, 0.2, 3))

        particles.arrange_submobjects_in_grid(buff=LARGE_BUFF)
        return particles

    def get_vector_field(self):
        func = get_force_field_func(*zip(
            map(Mobject.get_center, self.particles),
            [p.charge for p in self.particles]
        ))
        self.vector_field = VectorField(func, **self.vector_field_config)
        return self.vector_field


class InsertAirfoildTODO(TODOStub):
    CONFIG = {"message": "Insert airfoil flow animation"}


class ThreeDVectorField(ExternallyAnimatedScene):
    pass


class GravityFluidFlow(IntroduceVectorField):
    def construct(self):
        self.vector_field = VectorField(
            lambda p: np.array(ORIGIN),
            **self.vector_field_config
        )
        self.show_gravitational_force()
        self.show_fluid_flow()


class TotallyToScale(Scene):
    def construct(self):
        words = TextMobject(
            "Totally drawn to scale. \\\\ Don't even worry about it."
        )
        words.scale_to_fit_width(FRAME_WIDTH - 1)
        words.add_background_rectangle()
        self.add(words)
        self.wait()


# TODO: Revisit this
class FluidFlowAsHillGradient(Introduction, ThreeDScene):
    CONFIG = {
        "production_quality_flow": False,
    }

    def construct(self):
        def potential(point):
            x, y = point[:2]
            result = 2 - 0.01 * op.mul(
                ((x - 4)**2 + y**2),
                ((x + 4)**2 + y**2)
            )
            return max(-10, result)

        vector_field_func = negative_gradient(potential)

        stream_lines = StreamLines(
            vector_field_func,
            virtual_time=3,
            color_lines_by_magnitude=False,
            start_points_generator_config={
                "delta_x": 0.2,
                "delta_y": 0.2,
            }
        )
        for line in stream_lines:
            line.points[:, 2] = np.apply_along_axis(
                potential, 1, line.points
            )
        stream_lines_animation = self.get_stream_lines_animation(
            stream_lines
        )

        plane = NumberPlane()

        self.add(plane)
        self.add(stream_lines_animation)
        self.wait(3)
        self.begin_ambient_camera_rotation(rate=0.1)
        self.move_camera(
            phi=70 * DEGREES,
            run_time=2
        )
        self.wait(5)


class DefineDivergence(ChangingElectricField):
    CONFIG = {
        "vector_field_config": {
            "length_func": lambda norm: 0.3,
            "min_magnitude": 0,
            "max_magnitude": 1,
        },
        "stream_line_config": {
            "start_points_generator_config": {
                "delta_x": 0.125,
                "delta_y": 0.125,
            },
            "virtual_time": 2,
            "n_anchors_per_line": 10,
            "min_magnitude": 0,
            "max_magnitude": 1,
            "stroke_width": 2,
        },
        "stream_line_animation_config": {
            "line_anim_class": ShowPassingFlash,
        },
        "flow_time": 10,
        "random_seed": 7,
    }

    def construct(self):
        self.draw_vector_field()
        self.show_flow()
        self.point_out_sources_and_sinks()
        self.show_divergence_values()

    def draw_vector_field(self):
        particles = self.get_particles()
        random.shuffle(particles.submobjects)
        particles.remove(particles[0])
        particles.arrange_submobjects_in_grid(
            n_cols=4, buff=3
        )
        for particle in particles:
            particle.shift(
                np.random.normal(0, 0.75) * RIGHT,
                np.random.normal(0, 0.5) * UP,
            )
            particle.shift_onto_screen(buff=2 * LARGE_BUFF)
            particle.charge *= 0.125
        vector_field = self.get_vector_field()

        self.play(
            LaggedStart(GrowArrow, vector_field),
            LaggedStart(GrowFromCenter, particles),
            run_time=4
        )
        self.wait()
        self.play(LaggedStart(FadeOut, particles))

    def show_flow(self):
        stream_lines = StreamLines(
            self.vector_field.func,
            **self.stream_line_config
        )
        stream_line_animation = StreamLineAnimation(
            stream_lines,
            **self.stream_line_animation_config
        )
        self.add(stream_line_animation)
        self.wait(self.flow_time)

    def point_out_sources_and_sinks(self):
        particles = self.particles
        self.positive_points, self.negative_points = [
            [
                particle.get_center()
                for particle in particles
                if u * particle.charge > 0
            ]
            for u in +1, -1
        ]
        pair_of_vector_circle_groups = VGroup()
        for point_set in self.positive_points, self.negative_points:
            vector_circle_groups = VGroup()
            for point in point_set:
                vector_circle_group = VGroup()
                for angle in np.linspace(0, TAU, 12, endpoint=False):
                    step = 0.5 * rotate_vector(RIGHT, angle)
                    vect = self.vector_field.get_vector(point + step)
                    vect.set_color(WHITE)
                    vect.set_stroke(width=2)
                    vector_circle_group.add(vect)
                vector_circle_groups.add(vector_circle_group)
            pair_of_vector_circle_groups.add(vector_circle_groups)

            self.play(
                self.vector_field.set_fill, {"opacity": 0.5},
                LaggedStart(
                    LaggedStart, vector_circle_groups,
                    lambda vcg: (GrowArrow, vcg),
                ),
            )
            self.wait(4)
            self.play(FadeOut(vector_circle_groups))
        self.play(self.vector_field.set_fill, {"opacity": 1})
        self.positive_vector_circle_groups = pair_of_vector_circle_groups[0]
        self.negative_vector_circle_groups = pair_of_vector_circle_groups[1]
        self.wait()

    def show_divergence_values(self):
        positive_points = self.positive_points
        negative_points = self.negative_points
        div_func = divergence(self.vector_field.func)

        circle = Circle(color=WHITE, radius=0.2)
        circle.add(Dot(circle.get_center(), radius=0.02))
        circle.move_to(positive_points[0])

        div_tex = TexMobject(
            "\\text{div} \\, \\textbf{F}(x, y) = "
        )
        div_tex.add_background_rectangle()
        div_tex_update = ContinualUpdateFromFunc(
            div_tex, lambda m: m.next_to(circle, UP, SMALL_BUFF)
        )

        div_value = DecimalNumber(
            0,
            num_decimal_places=1,
            include_background_rectangle=True,
            include_sign=True,
        )
        div_value_update = ContinualChangingDecimal(
            div_value,
            lambda a: np.round(div_func(circle.get_center()), 1),
            position_update_func=lambda m: m.next_to(div_tex, RIGHT, SMALL_BUFF),
            include_sign=True,
        )

        self.play(
            ShowCreation(circle),
            FadeIn(div_tex),
            FadeIn(div_value),
        )
        self.add(div_tex_update)
        self.add(div_value_update)

        self.wait()
        for point in positive_points[1:-1]:
            self.play(circle.move_to, point)
            self.wait(1.5)
        for point in negative_points:
            self.play(circle.move_to, point)
            self.wait(2)
        self.wait(4)
        # self.remove(div_tex_update)
        # self.remove(div_value_update)
        # self.play(
        #     ApplyMethod(circle.scale, 0, remover=True),
        #     FadeOut(div_tex),
        #     FadeOut(div_value),
        # )


class DefineDivergenceJustFlow(DefineDivergence):
    CONFIG = {
        "flow_time": 10,
    }

    def construct(self):
        self.force_skipping()
        self.draw_vector_field()
        self.revert_to_original_skipping_status()
        self.clear()
        self.show_flow()


class DivergenceAtSlowFastPoint(Scene):
    CONFIG = {
        "vector_field_config": {
            "length_func": lambda norm: 0.1 + 0.4 * norm / 4.0,
            "min_magnitude": 0,
            "max_magnitude": 3,
        },
        "stream_lines_config": {
            "start_points_generator_config": {
                "delta_x": 0.125,
                "delta_y": 0.125,
            },
            "virtual_time": 1,
            "min_magnitude": 0,
            "max_magnitude": 3,
        },
    }

    def construct(self):
        def func(point):
            return 3 * sigmoid(point[0]) * RIGHT
        vector_field = self.vector_field = VectorField(
            func, **self.vector_field_config
        )

        circle = Circle(color=WHITE)
        slow_words = TextMobject("Slow flow in")
        fast_words = TextMobject("Fast flow out")
        words = VGroup(slow_words, fast_words)
        for word, vect in zip(words, [LEFT, RIGHT]):
            word.add_background_rectangle()
            word.next_to(circle, vect)

        div_tex = TexMobject(
            "\\text{div}\\,\\textbf{F}(x, y) > 0"
        )
        div_tex.add_background_rectangle()
        div_tex.next_to(circle, UP)

        self.add(vector_field)
        self.add_foreground_mobjects(circle, div_tex)
        self.begin_flow()
        self.wait(2)
        for word in words:
            self.add_foreground_mobjects(word)
            self.play(Write(word))
        self.wait(8)

    def begin_flow(self):
        stream_lines = StreamLines(
            self.vector_field.func,
            **self.stream_lines_config
        )
        stream_line_animation = StreamLineAnimation(stream_lines)
        stream_line_animation.update(3)
        self.add(stream_line_animation)


class DivergenceAsNewFunction(Scene):
    def construct(self):
        self.add_plane()
        self.show_vector_field_function()
        self.show_divergence_function()

    def add_plane(self):
        plane = self.plane = NumberPlane()
        plane.add_coordinates()
        self.add(plane)

    def show_vector_field_function(self):
        func = self.func
        unscaled_vector_field = VectorField(
            func,
            length_func=lambda norm: norm,
            colors=[BLUE_C, YELLOW, RED],
            delta_x=np.inf,
            delta_y=np.inf,
        )

        in_dot = Dot(color=PINK)
        in_dot.move_to(3.75 * LEFT + 1.25 * UP)

        def get_input():
            return in_dot.get_center()

        def get_out_vect():
            return unscaled_vector_field.get_vector(get_input())

        # Tex
        func_tex = TexMobject(
            "\\textbf{F}(", "+0.00", ",", "+0.00", ")", "=",
        )
        dummy_in_x, dummy_in_y = func_tex.get_parts_by_tex("+0.00")
        func_tex.add_background_rectangle()
        rhs = DecimalMatrix(
            [[0], [0]],
            element_to_mobject_config={
                "num_decimal_places": 2,
                "include_sign": True,
            },
            include_background_rectangle=True
        )
        rhs.next_to(func_tex, RIGHT)
        dummy_out_x, dummy_out_y = rhs.get_mob_matrix().flatten()

        VGroup(func_tex, rhs).to_corner(UL, buff=MED_SMALL_BUFF)

        VGroup(
            dummy_in_x, dummy_in_y,
            dummy_out_x, dummy_out_y,
        ).set_fill(BLACK, opacity=0)

        # Changing decimals
        in_x, in_y, out_x, out_y = [
            DecimalNumber(0, include_sign=True)
            for x in range(4)
        ]
        VGroup(in_x, in_y).set_color(in_dot.get_color())
        VGroup(out_x, out_y).set_color(get_out_vect().get_fill_color())
        in_x_update = ContinualChangingDecimal(
            in_x, lambda a: get_input()[0],
            position_update_func=lambda m: m.move_to(dummy_in_x)
        )
        in_y_update = ContinualChangingDecimal(
            in_y, lambda a: get_input()[1],
            position_update_func=lambda m: m.move_to(dummy_in_y)
        )
        out_x_update = ContinualChangingDecimal(
            out_x, lambda a: func(get_input())[0],
            position_update_func=lambda m: m.move_to(dummy_out_x)
        )
        out_y_update = ContinualChangingDecimal(
            out_y, lambda a: func(get_input())[1],
            position_update_func=lambda m: m.move_to(dummy_out_y)
        )

        self.add(func_tex, rhs)
        # self.add(ContinualUpdateFromFunc(
        #     rhs, lambda m: m.next_to(func_tex, RIGHT)
        # ))

        # Where those decimals actually change
        self.add(in_x_update, in_y_update)

        in_dot.save_state()
        in_dot.move_to(ORIGIN)
        self.play(in_dot.restore)
        self.wait()
        self.play(*[
            ReplacementTransform(
                VGroup(mob.copy().fade(1)),
                VGroup(out_x, out_y),
            )
            for mob in in_x, in_y
        ])
        out_vect = get_out_vect()
        VGroup(out_x, out_y).match_style(out_vect)
        out_vect.save_state()
        out_vect.move_to(rhs)
        out_vect.set_fill(opacity=0)
        self.play(out_vect.restore)
        self.out_vect_update = ContinualUpdateFromFunc(
            out_vect,
            lambda ov: Transform(ov, get_out_vect()).update(1)
        )

        self.add(self.out_vect_update)
        self.add(out_x_update, out_y_update)

        self.add(ContinualUpdateFromFunc(
            VGroup(out_x, out_y),
            lambda m: m.match_style(out_vect)
        ))
        self.wait()

        for vect in DOWN, 2 * RIGHT, UP:
            self.play(
                in_dot.shift, 3 * vect,
                run_time=3
            )
            self.wait()

        self.in_dot = in_dot
        self.out_vect = out_vect
        self.func_equation = VGroup(func_tex, rhs)
        self.out_x, self.out_y = out_x, out_y
        self.in_x, self.in_y = out_x, out_y
        self.in_x_update = in_x_update
        self.in_y_update = in_y_update
        self.out_x_update = out_x_update
        self.out_y_update = out_y_update

    def show_divergence_function(self):
        vector_field = VectorField(self.func)
        vector_field.remove(*[
            v for v in vector_field
            if v.get_start()[0] < 0 and v.get_start()[1] > 2
        ])
        vector_field.set_fill(opacity=0.5)
        in_dot = self.in_dot

        def get_neighboring_points(step_sizes=[0.3], n_angles=12):
            point = in_dot.get_center()
            return list(it.chain(*[
                [
                    point + step_size * step
                    for step in compass_directions(n_angles)
                ]
                for step_size in step_sizes
            ]))

        def get_vector_ring():
            return VGroup(*[
                vector_field.get_vector(point)
                for point in get_neighboring_points()
            ])

        def get_stream_lines():
            return StreamLines(
                self.func,
                start_points_generator=get_neighboring_points,
                start_points_generator_config={
                    "step_sizes": np.arange(0.1, 0.5, 0.1)
                },
                virtual_time=1,
                stroke_width=3,
            )

        def show_flow():
            stream_lines = get_stream_lines()
            random.shuffle(stream_lines.submobjects)
            self.play(LaggedStart(
                ShowCreationThenDestruction,
                stream_lines,
                remover=True
            ))

        vector_ring = get_vector_ring()
        vector_ring_update = ContinualUpdateFromFunc(
            vector_ring,
            lambda vr: Transform(vr, get_vector_ring()).update(1)
        )

        func_tex, rhs = self.func_equation
        out_x, out_y = self.out_x, self.out_y
        out_x_update = self.out_x_update
        out_y_update = self.out_y_update
        div_tex = TexMobject("\\text{div}")
        div_tex.add_background_rectangle()
        div_tex.move_to(func_tex, LEFT)
        div_tex.shift(2 * SMALL_BUFF * RIGHT)

        self.remove(out_x_update, out_y_update)
        self.remove(self.out_vect_update)
        self.add(self.in_x_update, self.in_y_update)
        self.play(
            func_tex.next_to, div_tex, RIGHT, SMALL_BUFF,
            {"submobject_to_align": func_tex[1][0]},
            Write(div_tex),
            FadeOut(self.out_vect),
            FadeOut(out_x),
            FadeOut(out_y),
            FadeOut(rhs),
        )
        # This line is a dumb hack around a Scene bug
        self.add(*[
            ContinualUpdateFromFunc(
                mob, lambda m: m.set_fill(None, 0)
            )
            for mob in out_x, out_y
        ])
        self.add_foreground_mobjects(div_tex)
        self.play(
            LaggedStart(GrowArrow, vector_field),
            LaggedStart(GrowArrow, vector_ring),
        )
        self.add(vector_ring_update)
        self.wait()

        div_func = divergence(self.func)
        div_rhs = DecimalNumber(
            0, include_sign=True,
            include_background_rectangle=True
        )
        div_rhs_update = ContinualChangingDecimal(
            div_rhs, lambda a: div_func(in_dot.get_center()),
            position_update_func=lambda d: d.next_to(func_tex, RIGHT, SMALL_BUFF)
        )

        self.play(FadeIn(div_rhs))
        self.add(div_rhs_update)
        show_flow()

        for vect in 2 * RIGHT, 3 * DOWN, 2 * LEFT, 2 * LEFT:
            self.play(in_dot.shift, vect, run_time=3)
            show_flow()
        self.wait()

    def func(self, point):
        x, y = point[:2]
        return np.sin(x + y) * RIGHT + np.sin(y * x / 3) * UP


class DivergenceZeroCondition(Scene):
    def construct(self):
        self.add_vector_field()
        self.add_title()
        self.begin_flow()
        self.add_circle()
        self.wait(5)

    def add_title(self):
        title = TextMobject(
            "For actual (incompressible) fluid flow:"
        )
        title.to_edge(UP)
        equation = TexMobject(
            "\\text{div} \\, \\textbf{F} = 0 \\quad \\text{everywhere}"
        )
        equation.next_to(title, DOWN)

        for mob in title, equation:
            mob.add_background_rectangle(buff=MED_SMALL_BUFF / 2)
            self.add_foreground_mobjects(mob)

    def add_vector_field(self):
        vector_field = VectorField(
            cylinder_flow_vector_field,
        )
        for vector in vector_field:
            if np.linalg.norm(vector.get_start()) < 1:
                vector_field.remove(vector)
        vector_field.set_fill(opacity=0.75)
        self.add_foreground_mobjects(vector_field)

    def begin_flow(self):
        stream_lines = StreamLines(
            cylinder_flow_vector_field,
            colors=[BLUE_E, BLUE_D, BLUE_C],
            start_points_generator_config={
                "delta_x": 0.125,
                "delta_y": 0.125,
            },
            virtual_time=5,
        )
        for stream_line in stream_lines:
            if np.linalg.norm(stream_line.points[0]) < 1:
                stream_lines.remove(stream_line)

        stream_line_animation = StreamLineAnimation(stream_lines)
        stream_line_animation.update(3)

        self.add(stream_line_animation)

    def add_circle(self):
        self.add_foreground_mobjects(Circle(
            radius=1,
            stroke_color=YELLOW,
            fill_color=BLACK,
            fill_opacity=1,
        ))


class IntroduceCurl(IntroduceVectorField):
    CONFIG = {
        "stream_line_animation_config": {
            "line_anim_class": ShowPassingFlash,
        },
        "stream_line_config": {
            "start_points_generator_config": {
                "delta_x": 0.125,
                "delta_y": 0.125,
            },
            "virtual_time": 1,
        }
    }

    def construct(self):
        self.add_title()
        self.show_vector_field()
        self.begin_flow()
        self.show_rotation()

    def add_title(self):
        title = self.title = Title(
            "Curl",
            match_underline_width_to_text=True,
            scale_factor=1.5,
        )
        title.add_background_rectangle()
        title.to_edge(UP, buff=MED_SMALL_BUFF)
        self.add_foreground_mobjects(title)

    def show_vector_field(self):
        vector_field = self.vector_field = VectorField(
            four_swirls_function,
            **self.vector_field_config
        )
        vector_field.submobjects.sort(
            lambda v1, v2: cmp(v1.get_length(), v2.get_length())
        )

        self.play(LaggedStart(GrowArrow, vector_field))
        self.wait()

    def begin_flow(self):
        stream_lines = StreamLines(
            self.vector_field.func,
            **self.stream_line_config
        )
        stream_line_animation = StreamLineAnimation(
            stream_lines,
            **self.stream_line_animation_config
        )

        self.add(stream_line_animation)
        self.wait(3)

    def show_rotation(self):
        clockwise_arrows, counterclockwise_arrows = [
            VGroup(*[
                self.get_rotation_arrows(clockwise=cw).move_to(point)
                for point in points
            ])
            for cw, points in [
                (True, [2 * UP, 2 * DOWN]),
                (False, [4 * LEFT, 4 * RIGHT]),
            ]
        ]

        for group, u in (counterclockwise_arrows, +1), (clockwise_arrows, -1):
            for arrows in group:
                label = TexMobject(
                    "\\text{curl} \\, \\textbf{F}",
                    ">" if u > 0 else "<",
                    "0"
                )
                label.add_background_rectangle()
                label.next_to(arrows, DOWN)
                self.add_foreground_mobjects(label)
                self.add(ContinualRotation(
                    arrows, rate=u * 30 * DEGREES
                ))
                self.play(
                    VFadeIn(arrows),
                    FadeIn(label)
                )
        self.wait(2)
        for group in counterclockwise_arrows, clockwise_arrows:
            self.play(FocusOn(group[0]))
            self.play(
                UpdateFromAlphaFunc(
                    group,
                    lambda mob, alpha: mob.set_color(
                        interpolate_color(WHITE, PINK, alpha)
                    ).set_stroke(
                        width=interpolate(5, 10, alpha)
                    ),
                    rate_func=there_and_back,
                    run_time=2
                )
            )
            self.wait()
        self.wait(6)

    # Helpers
    def get_rotation_arrows(self, clockwise=True, width=1):
        result = VGroup(*[
            Arrow(
                *points,
                use_rectangular_stem=False,
                buff=2 * SMALL_BUFF,
                path_arc=90 * DEGREES
            ).set_stroke(width=5)
            for points in adjacent_pairs(compass_directions(4, RIGHT))
        ])
        if clockwise:
            result.flip()
        result.scale_to_fit_width(width)
        return result


class ShearCurl(IntroduceCurl):
    def construct(self):
        self.show_vector_field()
        self.begin_flow()
        self.wait(2)
        self.comment_on_relevant_region()

    def show_vector_field(self):
        vector_field = self.vector_field = VectorField(
            self.func, **self.vector_field_config
        )
        vector_field.submobjects.sort(
            lambda a1, a2: cmp(a1.get_length(), a2.get_length())
        )
        self.play(LaggedStart(GrowArrow, vector_field))

    def comment_on_relevant_region(self):
        circle = Circle(color=WHITE, radius=0.75)
        circle.next_to(ORIGIN, UP, LARGE_BUFF)
        self.play(ShowCreation(circle))

        slow_words, fast_words = words = [
            TextMobject("Slow flow below"),
            TextMobject("Fast flow above")
        ]
        for word, vect in zip(words, [DOWN, UP]):
            word.add_background_rectangle(buff=SMALL_BUFF)
            word.next_to(circle, vect)
            self.add_foreground_mobjects(word)
            self.play(Write(word))
            self.wait()

        twig = Rectangle(
            height=0.8 * 2 * circle.radius,
            width=SMALL_BUFF,
            stroke_width=0,
            fill_color=GREY_BROWN,
            fill_opacity=1,
        )
        twig.add(Dot(twig.get_center()))
        twig.move_to(circle)
        twig_rotation = ContinualRotation(
            twig, rate=-90 * DEGREES,
            start_up_time=8,
        )

        self.play(FadeInAndShiftFromDirection(twig, UP))
        self.add(twig_rotation)
        self.wait(16)

    # Helpers
    def func(self, point):
        return 0.5 * point[1] * RIGHT


class FromKAWrapper(TeacherStudentsScene):
    def construct(self):
        screen = self.screen
        self.play(
            self.teacher.change, "raise_right_hand",
            self.get_student_changes(
                "pondering", "confused", "hooray",
            )
        )
        self.look_at(screen)
        self.wait(2)
        self.change_student_modes("erm", "happy", "confused")
        self.wait(3)
        self.teacher_says(
            "Our focus is \\\\ the 2d version",
            bubble_kwargs={"width": 4, "height": 3},
            added_anims=[self.get_student_changes(
                "happy", "hooray", "happy"
            )]
        )
        self.wait()


class ShowCurlAtVariousPoints(IntroduceCurl):
    CONFIG = {
        "func": four_swirls_function,
        "sample_points": [
            4 * RIGHT,
            2 * UP,
            4 * LEFT,
            2 * DOWN,
            ORIGIN,
            3 * RIGHT + 2 * UP,
            3 * LEFT + 2 * UP,
        ],
        "vector_field_config": {
            "fill_opacity": 0.75
        },
        "stream_line_config": {
            "virtual_time": 5,
            "start_points_generator_config": {
                "delta_x": 0.25,
                "delta_y": 0.25,
            }
        }
    }

    def construct(self):
        self.add_plane()
        self.show_vector_field()
        self.begin_flow()
        self.show_curl_at_points()

    def add_plane(self):
        plane = NumberPlane()
        plane.add_coordinates()
        self.add(plane)
        self.plane = plane

    def show_curl_at_points(self):
        dot = Dot()
        circle = Circle(radius=0.25, color=WHITE)
        circle.move_to(dot)
        circle_update = ContinualUpdateFromFunc(
            circle,
            lambda m: m.move_to(dot)
        )

        curl_tex = TexMobject(
            "\\text{curl} \\, \\textbf{F}(x, y) = "
        )
        curl_tex.add_background_rectangle(buff=0.025)
        curl_tex_update = ContinualUpdateFromFunc(
            curl_tex,
            lambda m: m.next_to(circle, UP, SMALL_BUFF)
        )

        curl_func = two_d_curl(self.func)
        curl_value = DecimalNumber(
            0, include_sign=True,
            include_background_rectangle=True,
        )
        curl_value_update = ContinualChangingDecimal(
            curl_value,
            lambda a: curl_func(dot.get_center()),
            position_update_func=lambda m: m.next_to(
                curl_tex, RIGHT, buff=0
            ),
            include_background_rectangle=True,
            include_sign=True,
        )

        points = self.sample_points
        self.add(dot, circle_update)
        self.play(
            dot.move_to, points[0],
            VFadeIn(dot),
            VFadeIn(circle),
        )
        curl_tex_update.update(0)
        curl_value_update.update(0)
        self.play(Write(curl_tex), FadeIn(curl_value))
        self.add(curl_tex_update, curl_value_update)
        self.wait()
        for point in points[1:]:
            self.play(dot.move_to, point, run_time=3)
            self.wait(2)
        self.wait(2)


class IllustrationUseVennDiagram(Scene):
    def construct(self):
        title = Title("Divergence \\& Curl")
        title.to_edge(UP, buff=MED_SMALL_BUFF)

        useful_for = TextMobject("Useful for")
        useful_for.next_to(title, DOWN)
        useful_for.set_color(BLUE)

        fluid_flow = TextMobject("Fluid \\\\ flow")
        fluid_flow.next_to(ORIGIN, UL)
        ff_circle = Circle(color=YELLOW)
        ff_circle.surround(fluid_flow, stretch=True)
        fluid_flow.match_color(ff_circle)

        big_circle = Circle(
            fill_color=BLUE,
            fill_opacity=0.2,
            stroke_color=BLUE,
        )
        big_circle.stretch_to_fit_width(9)
        big_circle.stretch_to_fit_height(6)
        big_circle.next_to(useful_for, DOWN, SMALL_BUFF)

        illustrated_by = TextMobject("Illustrated by")
        illustrated_by.next_to(
            big_circle.point_from_proportion(3. / 8), UL
        )
        illustrated_by.match_color(ff_circle)
        illustrated_by_arrow = Arrow(
            illustrated_by.get_bottom(),
            ff_circle.get_left(),
            path_arc=90 * DEGREES,
            use_rectangular_stem=False,
            color=YELLOW,
        )
        illustrated_by_arrow.pointwise_become_partial(
            illustrated_by_arrow, 0, 0.95
        )

        examples = VGroup(
            TextMobject("Electricity"),
            TextMobject("Magnetism"),
            TextMobject("Phase flow"),
            TextMobject("Stokes' theorem"),
        )
        points = [
            2 * RIGHT + 0.5 * UP,
            2 * RIGHT + 0.5 * DOWN,
            2 * DOWN,
            2 * LEFT + DOWN,
        ]
        for example, point in zip(examples, points):
            example.move_to(point)

        self.play(Write(title), run_time=1)
        self.play(
            Write(illustrated_by),
            ShowCreation(illustrated_by_arrow),
            run_time=1,
        )
        self.play(
            ShowCreation(ff_circle),
            FadeIn(fluid_flow),
        )
        self.wait()
        self.play(
            Write(useful_for),
            DrawBorderThenFill(big_circle),
            Animation(fluid_flow),
            Animation(ff_circle),
        )
        self.play(LaggedStart(
            FadeIn, examples,
            run_time=3,
        ))
        self.wait()


class MaxwellsEquations(Scene):
    CONFIG = {
        "faded_opacity": 0.3,
    }

    def construct(self):
        self.add_equations()
        self.circle_gauss_law()
        self.circle_magnetic_divergence()
        self.circle_curl_equations()

    def add_equations(self):
        title = Title("Maxwell's equations")
        title.to_edge(UP, buff=MED_SMALL_BUFF)

        tex_to_color_map = {
            "\\textbf{E}": BLUE,
            "\\textbf{B}": YELLOW,
            "\\rho": WHITE,
        }

        equations = self.equations = VGroup(*[
            TexMobject(
                tex, tex_to_color_map=tex_to_color_map
            )
            for tex in [
                """
                    \\text{div} \\, \\textbf{E} =
                    {\\rho \\over \\varepsilon_0}
                """,
                """\\text{div} \\, \\textbf{B} = 0""",
                """
                    \\text{curl} \\, \\textbf{E} =
                    -{\\partial \\textbf{B} \\over \\partial t}
                """,
                """
                    \\text{curl} \\, \\textbf{B} =
                    \\mu_0 \\left(
                        \\textbf{J} + \\varepsilon_0
                        {\\partial \\textbf{E} \\over \\partial t}
                    \\right)
                """,
            ]
        ])
        equations.arrange_submobjects(
            DOWN, aligned_edge=LEFT,
            buff=MED_LARGE_BUFF
        )

        field_definitions = VGroup(*[
            TexMobject(text, tex_to_color_map=tex_to_color_map)
            for text in [
                "\\text{Electric fild: } \\textbf{E}",
                "\\text{Magnetic fild: } \\textbf{B}",
            ]
        ])
        field_definitions.arrange_submobjects(
            RIGHT, buff=MED_LARGE_BUFF
        )
        field_definitions.next_to(title, DOWN, MED_LARGE_BUFF)
        equations.next_to(field_definitions, DOWN, MED_LARGE_BUFF)
        field_definitions.shift(MED_SMALL_BUFF * UP)

        self.add(title)
        self.add(field_definitions)
        self.play(LaggedStart(
            FadeIn, equations,
            run_time=3,
            lag_range=0.4
        ))
        self.wait()

    def circle_gauss_law(self):
        equation = self.equations[0]
        rect = SurroundingRectangle(equation)
        rect.set_color(RED)
        rho = equation.get_part_by_tex("\\rho")
        sub_rect = SurroundingRectangle(rho)
        sub_rect.match_color(rect)
        rho_label = TextMobject("Charge density")
        rho_label.next_to(sub_rect, RIGHT)
        rho_label.match_color(sub_rect)
        gauss_law = TextMobject("Gauss's law")
        gauss_law.next_to(rect, RIGHT)

        self.play(
            ShowCreation(rect),
            Write(gauss_law, run_time=1),
            self.equations[1:].set_fill, {"opacity": self.faded_opacity}
        )
        self.wait(2)
        self.play(
            ReplacementTransform(rect, sub_rect),
            FadeOut(gauss_law),
            FadeIn(rho_label),
            rho.match_color, sub_rect,
        )
        self.wait()
        self.play(
            self.equations.to_edge, LEFT,
            MaintainPositionRelativeTo(rho_label, equation),
            MaintainPositionRelativeTo(sub_rect, equation),
            VFadeOut(rho_label),
            VFadeOut(sub_rect),
        )
        self.wait()

    def circle_magnetic_divergence(self):
        equations = self.equations
        rect = SurroundingRectangle(equations[1])

        self.play(
            equations[0].set_fill, {"opacity": self.faded_opacity},
            equations[1].set_fill, {"opacity": 1.0},
        )
        self.play(ShowCreation(rect))
        self.wait(3)
        self.play(FadeOut(rect))

    def circle_curl_equations(self):
        equations = self.equations
        rect = SurroundingRectangle(equations[2:])
        randy = Randolph(height=2)
        randy.flip()
        randy.next_to(rect, RIGHT, aligned_edge=DOWN)
        randy.look_at(rect)

        self.play(
            equations[1].set_fill, {"opacity": self.faded_opacity},
            equations[2:].set_fill, {"opacity": 1.0},
        )
        self.play(ShowCreation(rect))
        self.play(
            randy.change, "confused",
            VFadeIn(randy),
        )
        self.play(Blink(randy))
        self.play(randy.look_at, 2 * RIGHT)
        self.wait(3)
        self.play(
            FadeOut(rect),
            randy.change, "pondering",
            randy.look_at, rect,
        )
        self.wait()
        self.play(Blink(randy))
        self.wait()


class IllustrateGaussLaw(DefineDivergence, MovingCameraScene):
    CONFIG = {
        "flow_time": 10,
        "stream_line_config": {
            "start_points_generator_config": {
                "delta_x": 1.0 / 16,
                "delta_y": 1.0 / 16,
                "x_min": -2,
                "x_max": 2,
                "y_min": -1.5,
                "y_max": 1.5,
            },
            "color_lines_by_magnitude": True,
            "colors": [BLUE_E, BLUE_D, BLUE_C],
            "stroke_width": 3,
        },
        "stream_line_animation_config": {
            "line_anim_class": ShowPassingFlashWithThinningStrokeWidth,
            "line_anim_config": {
                "n_segments": 5,
            }
        },
        "final_frame_width": 4,
    }

    def construct(self):
        particles = self.get_particles()
        vector_field = self.get_vector_field()

        self.add_foreground_mobjects(vector_field)
        self.add_foreground_mobjects(particles)
        self.zoom_in()
        self.show_flow()

    def get_particles(self):
        particles = VGroup(
            get_proton(radius=0.1),
            get_electron(radius=0.1),
        )
        particles.arrange_submobjects(RIGHT, buff=2.25)
        particles.shift(0.25 * UP)
        for particle, sign in zip(particles, [+1, -1]):
            particle.charge = sign

        self.particles = particles
        return particles

    def zoom_in(self):
        self.play(
            self.camera_frame.scale_to_fit_width, self.final_frame_width,
            run_time=2
        )


class IllustrateGaussMagnetic(IllustrateGaussLaw):
    CONFIG = {
        "final_frame_width": 7,
        "stream_line_config": {
            "start_points_generator_config": {
                "delta_x": 1.0 / 16,
                "delta_y": 1.0 / 16,
                "x_min": -3.5,
                "x_max": 3.5,
                "y_min": -2,
                "y_max": 2,
            },
            "color_lines_by_magnitude": True,
            "colors": [BLUE_E, BLUE_D, BLUE_C],
            "stroke_width": 3,
        },
        "flow_time": 10,
    }

    def construct(self):
        self.add_wires()
        self.show_vector_field()
        self.zoom_in()
        self.show_flow()

    def add_wires(self):
        top, bottom = [
            Circle(
                radius=0.275,
                stroke_color=WHITE,
                fill_color=BLACK,
                fill_opacity=1
            )
            for x in range(2)
        ]
        top.add(TexMobject("\\times").scale(0.5))
        bottom.add(Dot().scale(0.5))
        top.move_to(1 * UP)
        bottom.move_to(1 * DOWN)

        self.add_foreground_mobjects(top, bottom)

    def show_vector_field(self):
        vector_field = self.vector_field = VectorField(
            self.func, **self.vector_field_config
        )
        vector_field.submobjects.sort(
            lambda a1, a2: -cmp(a1.get_length(), a2.get_length())
        )
        self.play(LaggedStart(GrowArrow, vector_field))
        self.add_foreground_mobjects(
            vector_field, *self.foreground_mobjects
        )

    def func(self, point):
        x, y = point[:2]
        top_part = np.array([(y - 0.25), -x, 0])
        bottom_part = np.array([-(y + 0.25), x, 0])
        norm = np.linalg.norm
        return 3 * op.add(
            top_part / (norm(top_part)**2 + 1),
            bottom_part / (norm(bottom_part)**2 + 1),
        )


class IllustrateEMCurlEquations(ExternallyAnimatedScene):
    pass


class RelevantInNonSpatialCircumstances(TeacherStudentsScene):
    def construct(self):
        self.teacher_says(
            """
                $\\textbf{div}$ and $\\textbf{curl}$ are \\\\
                even useful in some \\\\
                non-spatial problems
            """,
            target_mode="hooray"
        )
        self.change_student_modes(
            "sassy", "confused", "hesitant"
        )
        self.wait(3)


class ShowTwoPopulations(Scene):
    CONFIG = {
        "total_num_animals": 50,
        "start_num_foxes": 20,
        "start_num_rabbits": 30,
        "animal_height": 0.5,
        "final_wait_time": 30,
    }

    def construct(self):
        self.introduce_animals()
        self.evolve_system()

    def introduce_animals(self):
        foxes = self.foxes = VGroup(*[
            self.get_fox()
            for n in range(self.total_num_animals)
        ])
        rabbits = self.rabbits = VGroup(*[
            self.get_rabbit()
            for n in range(self.total_num_animals)
        ])
        foxes[self.start_num_foxes:].set_fill(opacity=0)
        rabbits[self.start_num_rabbits:].set_fill(opacity=0)

        fox, rabbit = examples = VGroup(foxes[0], rabbits[0])
        for mob in examples:
            mob.save_state()
            mob.scale_to_fit_height(3)
        examples.arrange_submobjects(RIGHT, buff=2)

        preditor, prey = words = VGroup(
            TextMobject("Preditor"),
            TextMobject("Prey")
        )
        for mob, word in zip(examples, words):
            word.scale(1.5)
            word.next_to(mob, UP)
            self.play(
                FadeInFromDown(mob),
                Write(word, run_time=1),
            )
        self.play(
            LaggedStart(
                ApplyMethod, examples,
                lambda m: (m.restore,)
            ),
            LaggedStart(FadeOut, words),
            *[
                LaggedStart(
                    FadeIn,
                    group[1:],
                    run_time=4,
                    lag_ratio=0.1,
                )
                for group in [
                    foxes[:self.start_num_foxes],
                    rabbits[:self.start_num_rabbits],
                ]
            ]
        )

    def evolve_system(self):
        foxes = self.foxes
        rabbits = self.rabbits
        phase_point = VectorizedPoint(
            self.start_num_foxes * RIGHT +
            self.start_num_rabbits * UP
        )
        self.add(VectorFieldFlow(
            phase_point,
            preditor_prey_vector_field,
        ))

        def get_num_foxes():
            return phase_point.get_center()[0]

        def get_num_rabbits():
            return phase_point.get_center()[1]

        def get_updater(pop_size_getter):
            def update(animals):
                target_num = pop_size_getter()
                for n, animal in enumerate(animals):
                    animal.set_fill(
                        opacity=np.clip(target_num - n, 0, 1)
                    )
                target_int = int(np.ceil(target_num))
                tail = animals.submobjects[target_int:]
                random.shuffle(tail)
                animals.submobjects[target_int:] = tail

            return update

        self.add(ContinualUpdateFromFunc(
            foxes, get_updater(get_num_foxes)
        ))
        self.add(ContinualUpdateFromFunc(
            rabbits, get_updater(get_num_rabbits)
        ))

        # Add counts for foxes and rabbits
        labels = self.get_pop_labels()
        num_foxes = Integer(10)
        num_foxes.next_to(labels[0], RIGHT)
        num_rabbits = Integer(10)
        num_rabbits.next_to(labels[1], RIGHT)

        self.add(ContinualChangingDecimal(
            num_foxes, lambda a: get_num_foxes()
        ))
        self.add(ContinualChangingDecimal(
            num_rabbits, lambda a: get_num_rabbits()
        ))

        for count in num_foxes, num_rabbits:
            self.add(ContinualUpdateFromFunc(
                count, self.update_count_color,
            ))

        self.play(
            FadeIn(labels),
            *[
                UpdateFromAlphaFunc(count, lambda m, a: m.set_fill(opacity=a))
                for count in num_foxes, num_rabbits
            ]
        )

        self.wait(self.final_wait_time)

    # Helpers

    def get_animal(self, name, color):
        result = SVGMobject(
            file_name=name,
            height=self.animal_height,
            fill_color=color,
            # stroke_color=BLACK,
            # stroke_width=0.5
        )
        x_shift, y_shift = [
            (2 * random.random() - 1) * max_val
            for max_val in [
                FRAME_WIDTH / 2 - 2,
                FRAME_HEIGHT / 2 - 2
            ]
        ]
        result.shift(x_shift * RIGHT + y_shift * UP)
        return result

    def get_fox(self):
        return self.get_animal("fox", "#DF7F20")

    def get_rabbit(self):
        return self.get_animal("rabbit", WHITE)

    def get_pop_labels(self):
        labels = VGroup(
            TextMobject("\\# Foxes: "),
            TextMobject("\\# Rabbits: "),
        )
        labels.arrange_submobjects(RIGHT, buff=2)
        labels.to_edge(UP)
        return labels

    def update_count_color(self, count):
        count.set_fill(interpolate_color(
            BLUE, RED, (count.number - 20) / 30.0
        ))
        return count


class PhaseSpaceOfPopulationModel(ShowTwoPopulations):
    def construct(self):
        self.add_population_size_labels()
        self.add_axes()
        self.add_example_point()
        self.add_vectors()
        self.show_evolution_of_one_point()
        self.show_phase_flow()

    def add_population_size_labels(self):
        pass

    def add_axes(self):
        pass

    def add_example_point(self):
        pass

    def add_vectors(self):
        pass

    def show_evolution_of_one_point(self):
        pass

    def show_phase_flow(self):
        pass
